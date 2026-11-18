"""Detect what the operating system needs before php-build runs.

Two checks live here, apart from the installer itself: build flags that a
platform needs (position-independent code on x86_64 RHEL 8) and a check that
the build tools and libraries are installed. Both only read the system and set
environment variables; neither installs anything.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


def has_command(name: str) -> bool:
    return shutil.which(name) is not None


def append_env(name: str, value: str) -> None:
    current = os.environ.get(name, "")
    os.environ[name] = f"{current} {value}" if current else value


def read_os_release(os_release: Path = Path("/etc/os-release")) -> dict[str, str]:
    """Return the KEY=value fields of os-release, or an empty dict if unreadable."""
    try:
        text = os_release.read_text(encoding="utf-8")
    except OSError:
        return {}
    fields: dict[str, str] = {}
    for line in text.splitlines():
        key, separator, value = line.partition("=")
        if separator:
            fields[key] = value.strip().strip("\"'")
    return fields


def fields_are_rhel8(fields: Mapping[str, str]) -> bool:
    family = {fields.get("ID", ""), *fields.get("ID_LIKE", "").split()}
    return "rhel" in family and fields.get("VERSION_ID", "").split(".")[0] == "8"


def is_rhel8(os_release: Path = Path("/etc/os-release")) -> bool:
    """Return True on a RHEL 8 family system (RHEL, Rocky, Alma, CentOS 8)."""
    return fields_are_rhel8(read_os_release(os_release))


def setup_pie_for_rhel8() -> None:
    """Build position-independent code on x86_64 RHEL 8.

    GCC 8 and binutils 2.30 cannot link PHP's mbstring ifunc code into a
    non-PIE executable. The C++ flag is needed too: ext/intl otherwise fails
    to link into the PIE executable.
    """
    if platform.machine() != "x86_64" or not is_rhel8():
        return
    print("RHEL 8 detected, building with position-independent flags")
    for name, value in (
        ("CFLAGS", "-fPIE"),
        ("CXXFLAGS", "-fPIE"),
        ("LDFLAGS", "-pie"),
    ):
        if value not in os.getenv(name, "").split():
            append_env(name, value)


@dataclass(frozen=True)
class Requirement:
    """A build prerequisite and the package that provides it per package manager.

    ``kind`` is ``command`` (found on PATH), ``pkg-config`` (a .pc module) or
    ``header`` (a file under an include directory).
    """

    kind: str
    name: str
    apt: str
    dnf: str
    pacman: str


# Package names follow the lists in the README. Optional extensions (gmp,
# sodium, postgres) are not listed because the build works without them.
REQUIREMENTS = (
    Requirement("command", "autoconf", "autoconf", "autoconf", "autoconf"),
    Requirement("command", "bison", "bison", "bison", "bison"),
    Requirement("command", "re2c", "re2c", "re2c", "re2c"),
    Requirement("command", "make", "make", "make", "make"),
    Requirement("command", "gcc", "build-essential", "gcc", "gcc"),
    Requirement("command", "g++", "build-essential", "gcc-c++", "gcc"),
    Requirement("command", "pkg-config", "pkg-config", "pkgconf-pkg-config", "pkgconf"),
    Requirement("command", "bzip2", "bzip2", "bzip2", "bzip2"),
    Requirement("command", "find", "findutils", "findutils", "findutils"),
    Requirement("command", "xargs", "findutils", "findutils", "findutils"),
    Requirement("command", "diff", "diffutils", "diffutils", "diffutils"),
    Requirement("pkg-config", "libxml-2.0", "libxml2-dev", "libxml2-devel", "libxml2"),
    Requirement("pkg-config", "sqlite3", "libsqlite3-dev", "sqlite-devel", "sqlite"),
    Requirement(
        "pkg-config", "oniguruma", "libonig-dev", "oniguruma-devel", "oniguruma"
    ),
    Requirement(
        "pkg-config", "libcurl", "libcurl4-openssl-dev", "libcurl-devel", "curl"
    ),
    Requirement("pkg-config", "libzip", "libzip-dev", "libzip-devel", "libzip"),
    Requirement("pkg-config", "icu-i18n", "libicu-dev", "libicu-devel", "icu"),
    Requirement("pkg-config", "openssl", "libssl-dev", "openssl-devel", "openssl"),
    Requirement("pkg-config", "libxslt", "libxslt1-dev", "libxslt-devel", "libxslt"),
    Requirement("pkg-config", "zlib", "zlib1g-dev", "zlib-devel", "zlib"),
    # These libraries ship no pkg-config module, so their headers are checked.
    Requirement("header", "tidy.h", "libtidy-dev", "libtidy-devel", "tidy"),
    Requirement("header", "bzlib.h", "libbz2-dev", "bzip2-devel", "bzip2"),
    Requirement(
        "header", "jpeglib.h", "libjpeg-dev", "libjpeg-turbo-devel", "libjpeg-turbo"
    ),
    Requirement("header", "png.h", "libpng-dev", "libpng-devel", "libpng"),
    Requirement(
        "header",
        "readline/readline.h",
        "libreadline-dev",
        "readline-devel",
        "readline",
    ),
)

# On RHEL 8 re2c lives in EPEL and several -devel packages in PowerTools, so the
# install command fails until these repositories are enabled.
RHEL8_REPOSITORIES = (
    "sudo dnf install epel-release 'dnf-command(config-manager)'",
    "sudo dnf config-manager --set-enabled powertools",
)
RHEL8_SUBSCRIBED_REPOSITORIES = (
    "sudo subscription-manager repos --enable codeready-builder-for-rhel-8-$(arch)-rpms",
    "sudo dnf install https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm",
)

INSTALL_COMMANDS = {
    "apt": "sudo apt-get install -y",
    "dnf": "sudo dnf install",
    "pacman": "sudo pacman -S --needed",
}

# Debian and Ubuntu install the tidy headers below include/tidy/ (checked in the
# Ubuntu 24.04 libtidy-dev file list); Fedora and Rocky put them in include/.
HEADER_DIRECTORIES = (
    Path("/usr/include"),
    Path("/usr/include/tidy"),
    Path("/usr/local/include"),
    Path("/usr/local/include/tidy"),
)


def on_linux() -> bool:
    return sys.platform.startswith("linux")


def package_family(fields: Mapping[str, str]) -> str:
    """Return ``apt``, ``dnf`` or ``pacman`` for an os-release, or ``""``."""
    ids = {fields.get("ID", ""), *fields.get("ID_LIKE", "").split()}
    if ids & {"debian", "ubuntu"}:
        return "apt"
    if ids & {"rhel", "fedora", "centos"}:
        return "dnf"
    if "arch" in ids:
        return "pacman"
    return ""


def has_requirement(requirement: Requirement) -> bool:
    if requirement.kind == "command":
        return has_command(requirement.name)
    if requirement.kind == "header":
        return any((path / requirement.name).is_file() for path in HEADER_DIRECTORIES)
    try:
        result = subprocess.run(
            ["pkg-config", "--exists", requirement.name],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return False
    return result.returncode == 0


def missing_requirements(options: str) -> list[Requirement]:
    """Return the prerequisites that are absent, skipping ones the user replaced."""
    can_query = has_command("pkg-config")
    missing: list[Requirement] = []
    for requirement in REQUIREMENTS:
        # A chosen compiler is the user's own; a tidy option means they decided.
        if requirement.name == "gcc" and os.getenv("CC"):
            continue
        if requirement.name == "g++" and os.getenv("CXX"):
            continue
        if requirement.name == "tidy.h" and "tidy" in options:
            continue
        # Without pkg-config its modules cannot be checked; pkg-config itself is
        # reported as missing instead of every library behind it.
        if requirement.kind == "pkg-config" and not can_query:
            continue
        if not has_requirement(requirement):
            missing.append(requirement)
    return missing


def format_missing_requirements(
    missing: list[Requirement], fields: Mapping[str, str]
) -> str:
    names = ", ".join(requirement.name for requirement in missing)
    lines = [f"missing build prerequisites: {names}"]
    family = package_family(fields)
    if family:
        if fields_are_rhel8(fields):
            repositories = (
                RHEL8_SUBSCRIBED_REPOSITORIES
                if fields.get("ID") == "rhel"
                else RHEL8_REPOSITORIES
            )
            lines.append("If these repositories are not enabled yet, enable them first:")
            lines.extend(f"  {command}" for command in repositories)
        packages = dict.fromkeys(getattr(item, family) for item in missing)
        lines.append("Install them with:")
        lines.append(f"  {INSTALL_COMMANDS[family]} {' '.join(packages)}")
    lines.append("Set ASDF_PHP_SKIP_PREFLIGHT=yes to skip this check.")
    return "\n".join(lines)


def check_build_prerequisites(
    os_release: Path = Path("/etc/os-release"),
) -> None:
    """Stop with one clear message when build tools or libraries are missing.

    Without this check each missing piece fails deep inside php-build, one at a
    time, with an error that rarely names the package to install. Only Linux is
    checked: macOS dependencies come from Homebrew and are handled elsewhere.
    """
    if not on_linux() or os.getenv("ASDF_PHP_SKIP_PREFLIGHT", "no") != "no":
        return
    options = f"{os.getenv('PHP_BUILD_CONFIGURE_OPTS', '')} {os.getenv('PHP_CONFIGURE_OPTIONS', '')}"
    missing = missing_requirements(options)
    if missing:
        fields = read_os_release(os_release)
        raise RuntimeError(format_missing_requirements(missing, fields))
