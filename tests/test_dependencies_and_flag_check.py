"""Tests for the dependency and build-flag checks that run before php-build."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

LIB_DIR = Path(__file__).resolve().parents[1] / "lib"
sys.path.insert(0, str(LIB_DIR))
import dependencies_and_flag_check as checks


class DependencyCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        environment = patch.dict(os.environ, {}, clear=True)
        environment.start()
        self.addCleanup(environment.stop)

    def check_prerequisites(
        self, absent: set[str], os_release_text: str = 'ID="rocky"\nID_LIKE="rhel"\n'
    ) -> str:
        """Run the check with these requirement names absent; return the message."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os_release = Path(temp_dir) / "os-release"
            os_release.write_text(os_release_text, encoding="utf-8")
            with (
                patch.object(checks, "on_linux", return_value=True),
                patch.object(checks, "has_command", return_value=True),
                patch.object(
                    checks,
                    "has_requirement",
                    side_effect=lambda requirement: requirement.name not in absent,
                ),
            ):
                try:
                    checks.check_build_prerequisites(os_release)
                except RuntimeError as error:
                    return str(error)
        return ""

    def test_package_family_follows_id_and_id_like(self) -> None:
        self.assertEqual(checks.package_family({"ID": "ubuntu"}), "apt")
        mint = {"ID": "linuxmint", "ID_LIKE": "ubuntu debian"}
        rocky = {"ID": "rocky", "ID_LIKE": "rhel centos fedora"}
        self.assertEqual(checks.package_family(mint), "apt")
        self.assertEqual(checks.package_family({"ID": "fedora"}), "dnf")
        self.assertEqual(checks.package_family(rocky), "dnf")
        self.assertEqual(checks.package_family({"ID": "arch"}), "pacman")
        self.assertEqual(checks.package_family({"ID": "nixos"}), "")

    def test_prerequisites_pass_when_nothing_is_missing(self) -> None:
        self.assertEqual(self.check_prerequisites(set()), "")

    def test_missing_prerequisites_name_the_dnf_packages(self) -> None:
        message = self.check_prerequisites({"bzip2", "libxml-2.0", "tidy.h"})
        self.assertEqual(
            message,
            "missing build prerequisites: bzip2, libxml-2.0, tidy.h\n"
            "Install them with:\n"
            "  sudo dnf install bzip2 libxml2-devel libtidy-devel\n"
            "Set ASDF_PHP_SKIP_PREFLIGHT=yes to skip this check.",
        )

    def test_missing_prerequisites_name_the_apt_packages(self) -> None:
        message = self.check_prerequisites(
            {"bzip2", "libxml-2.0", "tidy.h"}, 'ID=ubuntu\nID_LIKE=debian\n'
        )
        self.assertIn(
            "  sudo apt-get install -y bzip2 libxml2-dev libtidy-dev\n", message
        )

    def test_missing_prerequisites_list_a_shared_package_once(self) -> None:
        message = self.check_prerequisites({"gcc", "g++"}, "ID=debian\n")
        self.assertIn("  sudo apt-get install -y build-essential\n", message)

    def test_unknown_distribution_gets_names_without_an_install_command(self) -> None:
        message = self.check_prerequisites({"bzip2"}, "ID=nixos\n")
        self.assertNotIn("Install them with", message)
        self.assertIn("missing build prerequisites: bzip2", message)

    def test_prerequisites_are_not_checked_off_linux(self) -> None:
        with (
            patch.object(checks, "on_linux", return_value=False),
            patch.object(checks, "has_command") as command_check,
        ):
            checks.check_build_prerequisites()
        command_check.assert_not_called()

    def test_prerequisite_check_can_be_skipped(self) -> None:
        os.environ["ASDF_PHP_SKIP_PREFLIGHT"] = "yes"
        with (
            patch.object(checks, "on_linux", return_value=True),
            patch.object(checks, "has_command") as command_check,
        ):
            checks.check_build_prerequisites()
        command_check.assert_not_called()

    def test_prerequisites_leave_a_chosen_compiler_and_tidy_choice_alone(self) -> None:
        os.environ.update(
            CC="clang", CXX="clang++", PHP_CONFIGURE_OPTIONS="--without-tidy"
        )
        message = self.check_prerequisites({"gcc", "g++", "tidy.h"})
        self.assertEqual(message, "")

    def test_library_checks_wait_for_pkg_config(self) -> None:
        with (
            patch.object(checks, "has_command", return_value=False),
            patch.object(checks, "has_requirement", return_value=False),
        ):
            names = {item.name for item in checks.missing_requirements("")}
        self.assertIn("pkg-config", names)
        self.assertNotIn("libxml-2.0", names)

    def test_header_requirement_looks_in_the_include_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "tidy.h").touch()
            requirement = checks.Requirement("header", "tidy.h", "a", "b", "c")
            with patch.object(checks, "HEADER_DIRECTORIES", (Path(temp_dir),)):
                self.assertTrue(checks.has_requirement(requirement))
            with patch.object(checks, "HEADER_DIRECTORIES", (Path(temp_dir) / "x",)):
                self.assertFalse(checks.has_requirement(requirement))

    def test_rocky_8_message_tells_you_to_enable_epel_and_powertools(self) -> None:
        message = self.check_prerequisites(
            {"re2c", "oniguruma"},
            'ID="rocky"\nID_LIKE="rhel centos fedora"\nVERSION_ID="8.10"\n',
        )
        self.assertIn("If these repositories are not enabled yet", message)
        self.assertIn("  sudo dnf install epel-release", message)
        self.assertIn("  sudo dnf config-manager --set-enabled powertools", message)
        self.assertLess(
            message.index("powertools"), message.index("  sudo dnf install re2c")
        )

    def test_rhel_8_message_uses_the_subscribed_repositories(self) -> None:
        message = self.check_prerequisites(
            {"re2c"}, 'ID="rhel"\nID_LIKE="fedora"\nVERSION_ID="8.10"\n'
        )
        self.assertIn("codeready-builder-for-rhel-8", message)
        self.assertNotIn("powertools", message)

    def test_repository_hint_is_only_for_rhel_8(self) -> None:
        rocky_9 = 'ID="rocky"\nID_LIKE="rhel centos fedora"\nVERSION_ID="9.4"\n'
        self.assertNotIn(
            "repositories", self.check_prerequisites({"re2c"}, rocky_9)
        )
        self.assertNotIn(
            "repositories",
            self.check_prerequisites({"re2c"}, "ID=ubuntu\nID_LIKE=debian\n"),
        )

    def test_libraries_without_pkg_config_are_checked_by_header(self) -> None:
        headers = {
            requirement.name: requirement
            for requirement in checks.REQUIREMENTS
            if requirement.kind == "header"
        }
        self.assertEqual(
            set(headers),
            {"tidy.h", "bzlib.h", "jpeglib.h", "png.h", "readline/readline.h"},
        )
        self.assertEqual(headers["bzlib.h"].dnf, "bzip2-devel")
        self.assertEqual(headers["readline/readline.h"].apt, "libreadline-dev")

    def test_nested_header_path_is_found_below_an_include_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "readline").mkdir()
            (Path(temp_dir) / "readline/readline.h").touch()
            requirement = checks.Requirement(
                "header", "readline/readline.h", "a", "b", "c"
            )
            with patch.object(checks, "HEADER_DIRECTORIES", (Path(temp_dir),)):
                self.assertTrue(checks.has_requirement(requirement))

    def test_tidy_header_is_found_in_the_ubuntu_tidy_directory(self) -> None:
        # libtidy-dev on Ubuntu 24.04 installs /usr/include/tidy/tidy.h only.
        tidy = next(item for item in checks.REQUIREMENTS if item.name == "tidy.h")
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "usr/include/tidy").mkdir(parents=True)
            (root / "usr/include/tidy/tidy.h").touch()
            real_directories = tuple(
                root / str(directory).lstrip("/")
                for directory in checks.HEADER_DIRECTORIES
            )
            with patch.object(checks, "HEADER_DIRECTORIES", real_directories):
                self.assertTrue(checks.has_requirement(tidy))
