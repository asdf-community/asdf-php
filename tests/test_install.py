"""Focused regression tests for the Python PHP installer helpers."""

from __future__ import annotations

import ast
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from collections.abc import Callable
from contextlib import redirect_stderr, redirect_stdout
from importlib.machinery import SourceFileLoader
from io import StringIO
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

LIB_DIR = Path(__file__).resolve().parents[1] / "lib"
sys.path.insert(0, str(LIB_DIR))
import install


def load_module(name: str, path: Path) -> ModuleType:
    """Import a module from a file whose name is not a valid identifier."""
    spec = importlib.util.spec_from_file_location(name, path)
    # The Python 3.9 stubs declare exec_module only on the concrete loader.
    if spec is None or not isinstance(spec.loader, SourceFileLoader):
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


OPENSSL_INSTALLER = load_module("install_openssl11", LIB_DIR / "install-openssl11.py")


def finds_only(*available: str) -> Callable[[str], bool]:
    """Return a stand-in for install.has_command that finds only these commands."""

    def has_command(name: str) -> bool:
        return name in available

    return has_command


def capture_output_clashes(*source_files: Path) -> list[str]:
    """Return file:line of calls mixing capture_output with stdout or stderr."""
    clashes: list[str] = []
    for source_file in source_files:
        tree = ast.parse(source_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            names = {keyword.arg for keyword in node.keywords}
            if "capture_output" in names and names & {"stdout", "stderr"}:
                clashes.append(f"{source_file.name}:{node.lineno}")
    return clashes


class InstallTests(unittest.TestCase):
    def setUp(self) -> None:
        environment = patch.dict(os.environ, {}, clear=True)
        environment.start()
        self.addCleanup(environment.stop)

    def test_php_parts_accepts_release_suffixes(self):
        self.assertEqual(install.php_parts("8.3.15RC1"), (8, 3, 15))

    def test_php_parts_rejects_invalid_version(self):
        with self.assertRaises(ValueError):
            install.php_parts("latest")

    def test_openssl_installer_uses_nproc_when_available(self):
        with (
            patch.object(
                OPENSSL_INSTALLER.shutil, "which", return_value="/usr/bin/nproc"
            ),
            patch.object(
                OPENSSL_INSTALLER,
                "run",
                return_value=subprocess.CompletedProcess([], 0, stdout="12"),
            ),
        ):
            self.assertEqual(OPENSSL_INSTALLER.build_jobs(), 12)

    def test_openssl_installer_falls_back_to_four_workers(self):
        with patch.object(OPENSSL_INSTALLER.shutil, "which", return_value=None):
            self.assertEqual(OPENSSL_INSTALLER.build_jobs(), 4)

    def test_concurrency_is_passed_through(self):
        os.environ["ASDF_CONCURRENCY"] = "8"
        install.setup_build_concurrency()
        self.assertEqual(os.environ["PHP_BUILD_EXTRA_MAKE_ARGUMENTS"], "-j8")

    def test_empty_concurrency_does_not_set_make_argument(self):
        install.setup_build_concurrency()
        self.assertNotIn("PHP_BUILD_EXTRA_MAKE_ARGUMENTS", os.environ)

    def test_optional_extensions_enable_installed_packages(self):
        with (
            patch.object(install, "has_command", return_value=True),
            patch.object(
                install, "run", return_value=subprocess.CompletedProcess([], 0)
            ),
        ):
            install.setup_optional_extensions()
        self.assertEqual(
            os.environ["PHP_BUILD_CONFIGURE_OPTS"], "--with-sodium --with-gmp"
        )

    def test_optional_extensions_leave_explicit_user_choice_alone(self):
        os.environ["PHP_CONFIGURE_OPTIONS"] = "--without-gmp"
        with (
            patch.object(install, "has_command", return_value=True),
            patch.object(install, "run") as run,
        ):
            install.setup_optional_extensions()
        run.assert_called_once_with(
            "pkg-config",
            "--exists",
            "libsodium",
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def test_missing_optional_extensions_only_report(self):
        with (
            patch.object(install, "has_command", return_value=True),
            patch.object(
                install, "run", return_value=subprocess.CompletedProcess([], 1)
            ),
            patch("builtins.print") as output,
        ):
            install.setup_optional_extensions()
        self.assertNotIn("PHP_BUILD_CONFIGURE_OPTS", os.environ)
        self.assertEqual(output.call_count, 2)

    def test_macos_without_brew_disables_tidy(self):
        with (
            patch.object(install, "on_macos", return_value=True),
            patch.object(install, "has_command", return_value=False),
        ):
            install.setup_macos_dependencies()
        self.assertEqual(os.environ["PHP_BUILD_CONFIGURE_OPTS"], "--without-tidy")

    def test_macos_without_tidy_html5_disables_tidy(self):
        with (
            patch.object(install, "on_macos", return_value=True),
            patch.object(install, "has_command", return_value=True),
            patch.object(install, "brew_prefix", return_value="/brew"),
            patch.object(
                install,
                "resolve_brew_package_prefix",
                side_effect=[
                    "/brew/opt/bzip2",
                    "/brew/opt/libiconv",
                    "/brew/opt/tidy-html5",
                ],
            ),
            patch.object(Path, "is_dir", return_value=False),
        ):
            install.setup_macos_dependencies()
        self.assertEqual(os.environ["PHP_BUILD_CONFIGURE_OPTS"], "--without-tidy")

    def test_macos_preserves_explicit_tidy_setting(self):
        os.environ["PHP_CONFIGURE_OPTIONS"] = "--with-tidy=/custom/tidy"
        with (
            patch.object(install, "on_macos", return_value=True),
            patch.object(install, "has_command", return_value=False),
        ):
            install.setup_macos_dependencies()
        self.assertNotIn("PHP_BUILD_CONFIGURE_OPTS", os.environ)

    def test_brew_dependency_configuration_is_idempotent(self):
        with (
            patch.object(install, "on_macos", return_value=True),
            patch.object(install, "has_command", return_value=True),
            patch.object(install, "brew_prefix", return_value="/brew"),
            patch.object(
                install,
                "resolve_brew_package_prefix",
                side_effect=[
                    "/brew/opt/bzip2",
                    "/brew/opt/libiconv",
                    "/brew/opt/tidy-html5",
                ]
                * 2,
            ),
            patch.object(Path, "is_dir", return_value=True),
        ):
            install.setup_macos_dependencies()
            install.setup_macos_dependencies()
        options = os.environ["PHP_BUILD_CONFIGURE_OPTS"]
        self.assertEqual(options.count("--with-tidy="), 1)
        self.assertEqual(options.count("--with-bz2="), 1)
        self.assertEqual(options.count("--with-iconv="), 1)
        self.assertEqual(os.environ["LDFLAGS"].count("-L/brew/lib"), 1)
        self.assertEqual(os.environ["CPPFLAGS"].count("-I/brew/include"), 1)

    def test_openssl_pin_uses_brew_prefix(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            prefix = Path(temp_dir) / "openssl@3"
            (prefix / "lib/pkgconfig").mkdir(parents=True)
            with (
                patch.object(install, "on_macos", return_value=True),
                patch.object(install, "has_command", return_value=True),
                patch.object(install, "brew_prefix", return_value=str(prefix)),
            ):
                install.setup_openssl_pin()
            self.assertEqual(os.environ["PKG_CONFIG_PATH"], f"{prefix}/lib/pkgconfig")
            self.assertIn(
                f"--with-openssl={prefix}", os.environ["PHP_BUILD_CONFIGURE_OPTS"]
            )

    def test_openssl_pin_comes_before_existing_search_paths(self):
        os.environ["PKG_CONFIG_PATH"] = "/other/pkgconfig"
        os.environ["LDFLAGS"] = "-L/opt/homebrew/lib"
        with (
            patch.object(install, "on_macos", return_value=True),
            patch.object(install, "has_command", return_value=True),
            patch.object(install, "brew_prefix", return_value="/brew/opt/openssl@3"),
            patch.object(Path, "is_dir", return_value=True),
        ):
            install.setup_openssl_pin()
        self.assertEqual(
            os.environ["PKG_CONFIG_PATH"],
            "/brew/opt/openssl@3/lib/pkgconfig:/other/pkgconfig",
        )
        self.assertEqual(
            os.environ["LDFLAGS"], "-L/brew/opt/openssl@3/lib -L/opt/homebrew/lib"
        )

    def test_openssl_pin_respects_existing_configuration(self):
        os.environ["PHP_CONFIGURE_OPTIONS"] = "--with-openssl=/custom"
        with (
            patch.object(install, "on_macos", return_value=True),
            patch.object(install, "has_command", return_value=True),
            patch.object(install, "brew_prefix") as brew,
        ):
            install.setup_openssl_pin()
        brew.assert_not_called()

    def test_cxxflags_are_upgraded_for_php_85(self):
        os.environ["CXXFLAGS"] = "-O2 -std=c++11"
        install.sanitize_cxxflags_for_modern_php("8.5.4")
        self.assertEqual(os.environ["CXXFLAGS"], "-O2 -std=c++17")

    def test_cxxflags_are_unchanged_before_icu_threshold(self):
        os.environ["CXXFLAGS"] = "-O2 -std=c++11"
        install.sanitize_cxxflags_for_modern_php("8.3.6")
        self.assertEqual(os.environ["CXXFLAGS"], "-O2 -std=c++11")

    def test_cxxflags_are_upgraded_at_php_minor_thresholds(self):
        for version in ("8.1.33", "8.2.19", "8.3.7", "8.4.0"):
            with self.subTest(version=version):
                os.environ["CXXFLAGS"] = "-std=c++11"
                install.sanitize_cxxflags_for_modern_php(version)
                self.assertEqual(os.environ["CXXFLAGS"], "-std=c++17")

    def test_brew_prefix_repairs_stale_opt_symlink(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cellar = root / "Cellar/bzip2/1.0"
            (cellar / "include").mkdir(parents=True)
            opt = root / "opt/bzip2"
            opt.parent.mkdir()
            opt.symlink_to(root / "missing")
            with (
                patch.object(install, "brew_prefix", return_value=str(opt)),
                patch.object(
                    install,
                    "run",
                    return_value=subprocess.CompletedProcess(
                        [], 0, stdout=str(root / "Cellar/bzip2")
                    ),
                ),
            ):
                self.assertEqual(install.resolve_brew_package_prefix("bzip2"), str(opt))
            self.assertTrue((opt / "include").is_dir())

    def test_patch_insertion_is_ordered_and_idempotent(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            definition = Path(temp_dir) / "8.0.19"
            definition.write_text('patch_file "first.patch"\ninstall_package "php"\n')
            self.assertTrue(
                install.insert_patch(definition, "second.patch", "first.patch")
            )
            self.assertFalse(
                install.insert_patch(definition, "second.patch", "first.patch")
            )
            self.assertEqual(
                definition.read_text(),
                'patch_file "first.patch"\npatch_file "second.patch"\ninstall_package "php"\n',
            )

    def test_main_requires_asdf_install_environment(self):
        with (
            patch.object(Path, "is_file", return_value=True),
            redirect_stderr(StringIO()),
        ):
            self.assertEqual(install.main(Path("/plugin")), 2)

    def test_main_runs_the_build_and_writes_default_php_ini(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            plugin_dir = Path(temp_dir)
            install_path = plugin_dir / "installed-php"
            (plugin_dir / "vendor/php-build/bin").mkdir(parents=True)
            (plugin_dir / "vendor/php-build/bin/php-build").touch()
            with (
                patch.dict(
                    os.environ,
                    {
                        "ASDF_INSTALL_VERSION": "8.5.4",
                        "ASDF_INSTALL_PATH": str(install_path),
                    },
                    clear=True,
                ),
                patch.object(install, "setup_macos_dependencies"),
                patch.object(install, "setup_optional_extensions"),
                patch.object(install, "configure_openssl11"),
                patch.object(install, "setup_openssl_pin"),
                patch.object(install, "setup_compiler_for_old_php"),
                patch.object(install, "setup_build_concurrency"),
                patch.object(install, "patch_php_build_definitions"),
                patch.object(install, "sanitize_cxxflags_for_modern_php"),
                patch.object(install, "run") as run,
            ):
                self.assertEqual(install.main(plugin_dir), 0)
            run.assert_called_once_with(
                str(plugin_dir / "vendor/php-build/bin/php-build"),
                "8.5.4",
                str(install_path),
            )
            self.assertEqual(
                (install_path / "conf.d/php.ini").read_text(),
                "# Add custom PHP configuration here\n",
            )

    def test_old_php_build_adds_compatibility_flags(self):
        with (
            patch.object(install, "on_macos", return_value=False),
            patch.object(install, "has_command", side_effect=finds_only("gcc")),
            patch.object(
                install, "run", return_value=subprocess.CompletedProcess([], 0)
            ),
        ):
            install.setup_compiler_for_old_php("8.0.19")
        self.assertIn(
            "-Wno-incompatible-pointer-types-discards-qualifiers", os.environ["CFLAGS"]
        )
        self.assertIn("--without-tidy", os.environ["PHP_BUILD_CONFIGURE_OPTS"])
        self.assertEqual(os.environ["MAKE_OPTS"], "-j1")

    def test_modern_php_does_not_run_old_compiler_setup(self):
        with patch.object(install, "has_command") as command_check:
            install.setup_compiler_for_old_php("8.5.4")
        command_check.assert_not_called()

    def test_definition_patches_are_copied_and_inserted_in_order(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plugin = root / "plugin"
            build = root / "php-build"
            patch_source = plugin / "patches"
            patch_source.mkdir(parents=True)
            for name in (
                "php-8.0-libxml2-2.12-compat.patch",
                "php-8.0-icu-74-compat.patch",
                "php-8.0-intl-cxx17.patch",
            ):
                (patch_source / name).write_text("patch\n")
            definitions = build / "share/php-build/definitions"
            definitions.mkdir(parents=True)
            definition = definitions / "8.0.19"
            definition.write_text(
                'patch_file "php-8.0-support-openssl-3.patch"\ninstall_package "php"\n'
            )
            install.patch_php_build_definitions("8.0.19", plugin, build)
            result = definition.read_text()
            self.assertLess(
                result.index("php-8.0-libxml2-2.12-compat.patch"),
                result.index("php-8.0-icu-74-compat.patch"),
            )
            self.assertLess(
                result.index("php-8.0-icu-74-compat.patch"),
                result.index("php-8.0-intl-cxx17.patch"),
            )
            self.assertTrue(
                (build / "share/php-build/patches/php-8.0-intl-cxx17.patch").is_file()
            )

class RealSubprocessTests(unittest.TestCase):
    """Run the helpers against real child processes.

    The tests above patch ``run``, so a keyword that clashes with
    ``subprocess.run`` can only fail here.
    """

    def setUp(self) -> None:
        environment = patch.dict(os.environ, {}, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
        commands = tempfile.TemporaryDirectory()
        self.addCleanup(commands.cleanup)
        os.environ["PATH"] = commands.name

    def make_command(
        self, name: str, script: str, directory: Path | None = None
    ) -> Path:
        """Write an executable shell script, by default as the only PATH entry."""
        command = (directory or Path(os.environ["PATH"])) / name
        command.write_text(f"#!/bin/sh\n{script}\n", encoding="utf-8")
        command.chmod(0o755)
        return command

    def make_shared_openssl(self, prefix: Path) -> Path:
        """Write an openssl that starts only when its own lib directory is searched.

        A fresh shared build has no rpath, so on Linux it needs LD_LIBRARY_PATH.
        """
        (prefix / "bin").mkdir(parents=True)
        return self.make_command(
            "openssl",
            f"""case ":$LD_LIBRARY_PATH:" in
  *":{prefix}/lib:"*) echo 'OpenSSL 1.1.1w  11 Sep 2023' ;;
  *) echo 'libssl.so.1.1: cannot open shared object file' >&2; exit 127 ;;
esac""",
            directory=prefix / "bin",
        )

    def test_run_lets_the_caller_choose_stdout(self) -> None:
        result = install.run(
            sys.executable, "-c", "print('x')", stdout=subprocess.DEVNULL
        )
        self.assertIsNone(result.stdout)

    def test_run_capture_returns_the_output(self) -> None:
        result = install.run(sys.executable, "-c", "print('x')", capture=True)
        self.assertEqual(result.stdout, "x\n")

    def test_optional_extensions_follow_pkg_config(self) -> None:
        self.make_command("pkg-config", "exit 0")
        install.setup_optional_extensions()
        self.assertEqual(
            os.environ["PHP_BUILD_CONFIGURE_OPTS"], "--with-sodium --with-gmp"
        )

    def test_xdebug_install_writes_the_ini_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            install_path = Path(temp_dir)
            (install_path / "bin").mkdir()
            (install_path / "conf.d").mkdir()
            self.make_command("pecl", "exit 0", directory=install_path / "bin")
            with redirect_stdout(StringIO()):
                installed = install.install_xdebug(install_path)
            ini = (install_path / "conf.d/xdebug.ini").read_text(encoding="utf-8")
        self.assertTrue(installed)
        self.assertIn("zend_extension=xdebug.so", ini)

    def test_openssl_installer_reads_the_job_count_from_nproc(self) -> None:
        self.make_command("nproc", "echo 6")
        self.assertEqual(OPENSSL_INSTALLER.build_jobs(), 6)

    def test_openssl_installer_reports_an_existing_installation(self) -> None:
        output = StringIO()
        with tempfile.TemporaryDirectory() as temp_dir:
            prefix = Path(temp_dir)
            self.make_shared_openssl(prefix)
            os.environ["INSTALL_PREFIX"] = str(prefix)
            with redirect_stdout(output):
                status = OPENSSL_INSTALLER.main(["--auto"])
        self.assertEqual(status, 0)
        self.assertIn(
            f"OpenSSL 1.1 already installed: 1.1.1w at {prefix}", output.getvalue()
        )

    def test_openssl_version_check_searches_the_install_libraries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            prefix = Path(temp_dir)
            self.make_shared_openssl(prefix)
            version = OPENSSL_INSTALLER.installed_version(prefix)
        self.assertEqual(version, "1.1.1w")

    def test_openssl_version_check_keeps_the_callers_library_path(self) -> None:
        os.environ["LD_LIBRARY_PATH"] = "/caller/lib"
        with tempfile.TemporaryDirectory() as temp_dir:
            prefix = Path(temp_dir)
            (prefix / "bin").mkdir()
            self.make_command(
                "openssl", 'echo "OpenSSL $LD_LIBRARY_PATH"', directory=prefix / "bin"
            )
            version = OPENSSL_INSTALLER.installed_version(prefix)
        self.assertEqual(version, f"{prefix}/lib:/caller/lib")

    def test_openssl_version_check_leaves_no_empty_library_path_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            prefix = Path(temp_dir)
            (prefix / "bin").mkdir()
            self.make_command(
                "openssl", 'echo "OpenSSL $LD_LIBRARY_PATH"', directory=prefix / "bin"
            )
            version = OPENSSL_INSTALLER.installed_version(prefix)
        self.assertEqual(version, f"{prefix}/lib")

    def test_openssl_version_check_is_none_when_the_binary_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            prefix = Path(temp_dir)
            (prefix / "bin").mkdir()
            self.make_command("openssl", "exit 127", directory=prefix / "bin")
            version = OPENSSL_INSTALLER.installed_version(prefix)
        self.assertIsNone(version)


class SubprocessKeywordTests(unittest.TestCase):
    def test_lib_never_mixes_capture_output_with_stdout_or_stderr(self) -> None:
        # subprocess.run raises ValueError for that mix, and only when the call runs.
        clashes = capture_output_clashes(
            LIB_DIR / "install.py", LIB_DIR / "install-openssl11.py"
        )
        self.assertEqual(clashes, [])


if __name__ == "__main__":
    unittest.main()
