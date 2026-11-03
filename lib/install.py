"""Configure and run php-build for one asdf PHP installation."""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path


def run(
    *args: str,
    check: bool = True,
    capture: bool = False,
    stdout: int | None = None,
    stderr: int | None = None,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a child command with the current build environment.

    ``capture`` pipes stdout unless the caller passes its own ``stdout``.
    """
    if capture and stdout is None:
        # A caller's own stdout wins, because subprocess.run rejects a second one.
        stdout = subprocess.PIPE
    try:
        return subprocess.run(
            args, check=check, text=True, stdout=stdout, stderr=stderr, cwd=cwd, env=env
        )
    except FileNotFoundError:
        if check:
            raise
        return subprocess.CompletedProcess(args, 127, stdout="" if capture else None)


def has_command(name: str) -> bool:
    return shutil.which(name) is not None


def on_macos() -> bool:
    return sys.platform.startswith("darwin") or os.getenv("OSTYPE", "").startswith(
        "darwin"
    )


def append_env(name: str, value: str, separator: str = " ") -> None:
    current = os.environ.get(name, "")
    os.environ[name] = f"{current}{separator if current else ''}{value}"


def prepend_env(name: str, value: str, separator: str = " ") -> None:
    current = os.environ.get(name, "")
    os.environ[name] = f"{value}{separator if current else ''}{current}"


def php_parts(version: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:[A-Za-z][A-Za-z0-9._-]*)?", version)
    if not match:
        raise ValueError(f"invalid PHP version: {version}")
    major, minor, patch = match.groups()
    return int(major), int(minor), int(patch)


def brew_prefix(package: str | None = None) -> str:
    args = ["brew", "--prefix"]
    if package:
        args.append(package)
    result = run(*args, check=False, capture=True, stderr=subprocess.DEVNULL)
    return result.stdout.strip() if result.returncode == 0 else ""


def resolve_brew_package_prefix(package: str) -> str:
    """Repair a stale Homebrew opt symlink and return its prefix."""
    opt_prefix = brew_prefix(package)
    if not opt_prefix:
        return ""
    opt_path = Path(opt_prefix)
    if not (opt_path / "include").is_dir():
        cellar = run(
            "brew",
            "--cellar",
            package,
            check=False,
            capture=True,
            stderr=subprocess.DEVNULL,
        )
        cellar_path = Path(cellar.stdout.strip()) if cellar.returncode == 0 else None
        if cellar_path and cellar_path.is_dir():
            versions = sorted(
                (p for p in cellar_path.iterdir() if p.is_dir()), key=lambda p: p.name
            )
            if versions and (versions[0] / "include").is_dir():
                if opt_path.is_symlink() or opt_path.is_file():
                    opt_path.unlink()
                elif opt_path.exists():
                    shutil.rmtree(opt_path)
                opt_path.symlink_to(versions[0])
    return opt_prefix


def setup_macos_dependencies() -> None:
    if not on_macos():
        return
    if not has_command("brew"):
        options = f"{os.getenv('PHP_BUILD_CONFIGURE_OPTS', '')} {os.getenv('PHP_CONFIGURE_OPTIONS', '')}"
        if "--with-tidy" not in options and "--without-tidy" not in options:
            append_env("PHP_BUILD_CONFIGURE_OPTS", "--without-tidy")
        return

    prefix = brew_prefix()
    packages = {
        name: resolve_brew_package_prefix(name)
        for name in ("bzip2", "libiconv", "tidy-html5")
    }
    options = f"{os.getenv('PHP_BUILD_CONFIGURE_OPTS', '')} {os.getenv('PHP_CONFIGURE_OPTIONS', '')}"
    if "--with-tidy" not in options and "--without-tidy" not in options:
        tidy = packages["tidy-html5"]
        append_env(
            "PHP_BUILD_CONFIGURE_OPTS",
            f"--with-tidy={tidy}" if tidy and Path(tidy).is_dir() else "--without-tidy",
        )
    for package, option in (("bzip2", "bz2"), ("libiconv", "iconv")):
        path = packages[package]
        if (
            path
            and Path(path).is_dir()
            and f"--with-{option}=" not in os.getenv("PHP_BUILD_CONFIGURE_OPTS", "")
        ):
            append_env("PHP_BUILD_CONFIGURE_OPTS", f"--with-{option}={path}")
    for name, value in (
        ("LDFLAGS", f"-L{prefix}/lib"),
        ("CPPFLAGS", f"-I{prefix}/include"),
    ):
        if value not in os.getenv(name, ""):
            append_env(name, value)


def setup_optional_extensions() -> None:
    configured = f"{os.getenv('PHP_BUILD_CONFIGURE_OPTS', '')} {os.getenv('PHP_CONFIGURE_OPTIONS', '')}"
    for package, extension in (("libsodium", "sodium"), ("gmp", "gmp")):
        if f"-{extension}" in configured:
            continue
        if (
            has_command("pkg-config")
            and run(
                "pkg-config",
                "--exists",
                package,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            ).returncode
            == 0
        ):
            append_env("PHP_BUILD_CONFIGURE_OPTS", f"--with-{extension}")
        else:
            print(f"{package} not found, building without the {extension} extension")


def setup_openssl_pin() -> None:
    if not on_macos() or not has_command("brew"):
        return
    options = f" {os.getenv('PHP_BUILD_CONFIGURE_OPTS', '')} {os.getenv('PHP_CONFIGURE_OPTIONS', '')} "
    if "--with-openssl" in options:
        return
    if "openssl" in os.getenv("PKG_CONFIG_PATH", "").split(":", 1)[0]:
        return
    prefix = brew_prefix("openssl@3")
    if not prefix or not (Path(prefix) / "lib/pkgconfig").is_dir():
        return
    # The search paths use the first match, so openssl@3 must come before the
    # generic -L and pkgconfig entries that are already set.
    prepend_env("PKG_CONFIG_PATH", f"{prefix}/lib/pkgconfig", ":")
    prepend_env("LDFLAGS", f"-L{prefix}/lib")
    # configure uses the last --with-openssl, so this overrides php-build's default.
    append_env("PHP_BUILD_CONFIGURE_OPTS", f"--with-openssl={prefix}")
    print(f"Using OpenSSL from {prefix} (openssl@4 headers do not build PHP 8.3)")


def sanitize_cxxflags_for_modern_php(version: str) -> None:
    major, minor, patch = php_parts(version)
    needs_cxx17 = major > 8 or (
        major == 8
        and (
            minor >= 4
            or (minor == 3 and patch >= 7)
            or (minor == 2 and patch >= 19)
            or (minor == 1 and patch >= 33)
        )
    )
    if not needs_cxx17:
        return
    flags = re.sub(r"-std=c\+\+[^ ]*", "", os.getenv("CXXFLAGS", "")).strip()
    if not flags and on_macos() and has_command("brew"):
        prefix = brew_prefix("icu4c")
        config = Path(prefix) / "bin/icu-config"
        if prefix and config.exists():
            result = run(
                str(config),
                "--version",
                check=False,
                capture=True,
                stderr=subprocess.DEVNULL,
            )
            try:
                icu_major = int(result.stdout.split(".", 1)[0])
            except (ValueError, IndexError):
                icu_major = 0
            if icu_major > 61:
                flags = "-stdlib=libc++ -DU_USING_ICU_NAMESPACE=1"
            elif icu_major > 59:
                flags = "-stdlib=libc++"
    os.environ["CXXFLAGS"] = f"{flags} -std=c++17".strip()


def configure_openssl11(version: str, plugin_dir: Path) -> None:
    try:
        openssl_version = run(
            "openssl", "version", capture=True, stderr=subprocess.DEVNULL
        ).stdout.split()[1]
        openssl_major = int(openssl_version.split(".", 1)[0])
    except (OSError, subprocess.CalledProcessError, IndexError, ValueError):
        print("⚠ Warning: OpenSSL not found in PATH")
        return
    major, minor, patch = php_parts(version)
    needs = (
        major == 7
        or (major == 8 and minor == 0 and patch < 20)
        or (major == 8 and minor == 1 and patch < 6)
    )
    if openssl_major < 3 or not needs:
        return
    print(f"⚠ PHP {version} incompatible with OpenSSL {openssl_version}")
    if major == 8 and minor == 0 and patch < 6:
        print(
            "⚠ PHP 8.0.0-8.0.5 have additional compatibility issues with modern systems\n  Recommended: Use PHP 8.0.30 (latest 8.0.x) instead"
        )
    candidates = [
        Path.home() / ".local/openssl-1.1",
        Path("/usr/local/openssl-1.1"),
        Path("/usr/local/openssl@1.1"),
        Path("/usr/local/opt/openssl@1.1"),
        Path("/opt/openssl-1.1"),
        Path("/usr/lib64/openssl11"),
    ]
    found = next(
        (path for path in candidates if (path / "bin/openssl").is_file()), None
    )
    if found:
        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = f"{found}/lib:{env.get('LD_LIBRARY_PATH', '')}"
        found_version = run(
            str(found / "bin/openssl"),
            "version",
            capture=True,
            stderr=subprocess.DEVNULL,
            env=env,
        ).stdout.split()[1]
        print(f"✓ Using OpenSSL 1.1 ({found_version}) at {found}")
    else:
        print(
            "✗ OpenSSL 1.1 not found\n\nphp-build's OpenSSL 3 patch is incomplete for PHP "
            + version
            + ".\nOpenSSL 1.1 is required to build this PHP version.\n"
        )
        auto = (
            any(
                os.getenv(key, default) == value
                for key, default, value in (
                    ("CI", "false", "true"),
                    ("GITHUB_ACTIONS", "false", "true"),
                )
            )
            or os.getenv("ASDF_PHP_OPENSSL_AUTO", "no") != "no"
        )
        if auto:
            print("Auto-installing OpenSSL 1.1 (CI environment detected)...")
        elif sys.stdin.isatty():
            auto = (
                input("Install OpenSSL 1.1 automatically? [y/N] ")
                .lower()
                .startswith("y")
            )
        else:
            raise RuntimeError(
                "Cannot prompt without a terminal; set ASDF_PHP_OPENSSL_AUTO=yes to continue"
            )
        if not auto:
            command = shlex.join(
                (sys.executable, str(plugin_dir / "lib/install-openssl11.py"))
            )
            raise RuntimeError(
                f"Cannot proceed without OpenSSL 1.1. To install manually, run: {command}"
            )
        installer = plugin_dir / "lib/install-openssl11.py"
        run(sys.executable, str(installer), "--auto")
        found = Path(
            os.getenv("INSTALL_PREFIX", str(Path.home() / ".local/openssl-1.1"))
        )
        if not (found / "bin/openssl").is_file():
            raise RuntimeError(
                f"OpenSSL 1.1 binary not found after installation: {found}"
            )
    prefix = str(found)
    os.environ["PKG_CONFIG_PATH"] = (
        f"{prefix}/lib/pkgconfig:{os.getenv('PKG_CONFIG_PATH', '')}"
    )
    append_env("PHP_BUILD_CONFIGURE_OPTS", f"--with-openssl={prefix}")
    os.environ["OPENSSL_CFLAGS"] = f"-I{prefix}/include"
    os.environ["OPENSSL_LIBS"] = f"-L{prefix}/lib -lssl -lcrypto"
    os.environ["LD_LIBRARY_PATH"] = f"{prefix}/lib:{os.getenv('LD_LIBRARY_PATH', '')}"


def setup_compiler_for_old_php(version: str) -> None:
    major, minor, patch = php_parts(version)
    php74 = major == 7 and minor == 4
    php80 = major == 8 and minor == 0 and patch < 20
    if not (php74 or php80):
        return
    print(f"=== Configuring compiler for PHP {version} ===")
    cc, cxx = (
        ("gcc-9", "g++-9")
        if has_command("gcc-9") and has_command("g++-9")
        else ("gcc", "g++")
    )
    if cc == "gcc-9":
        print("Using gcc-9/g++-9 for better compatibility")
    else:
        print("gcc-9 not available, using system gcc")
    os.environ.update(CC=cc, CXX=cxx, ac_cv_prog_CC=cc, ac_cv_prog_CXX=cxx)
    if not has_command(cc):
        raise RuntimeError(f"Compiler {cc} not found")
    with tempfile.TemporaryDirectory(prefix="asdf-php-cc-") as directory:
        source = Path(directory) / "test.c"
        binary = Path(directory) / "test"
        source.write_text("int main(void) { return 0; }\n")
        try:
            run(cc, "-o", str(binary), str(source), stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as error:
            raise RuntimeError("Compiler test failed") from error
    print("✓ Compiler test successful")
    if not os.environ.get("CXXFLAGS"):
        os.environ["CXXFLAGS"] = "-Wno-error -Wno-deprecated-declarations -O0"
    if php74:
        if not os.environ.get("CFLAGS"):
            os.environ["CFLAGS"] = (
                "-Wno-error -Wno-deprecated-declarations -Wno-implicit-function-declaration -Wno-int-conversion -Wno-stringop-overflow -O0"
            )
    else:
        if not os.environ.get("CFLAGS"):
            os.environ["CFLAGS"] = (
                "-Wno-error -Wno-deprecated-declarations -Wno-implicit-function-declaration -Wno-int-conversion -Wno-stringop-overflow -Wno-incompatible-pointer-types-discards-qualifiers -O0"
            )
        if (
            "-Wno-incompatible-pointer-types-discards-qualifiers"
            not in os.environ["CFLAGS"]
        ):
            append_env("CFLAGS", "-Wno-incompatible-pointer-types-discards-qualifiers")
    common = "--disable-werror --with-external-pcre --disable-fileinfo"
    if on_macos():
        if "-lresolv" not in os.getenv("LDFLAGS", "") and php74:
            append_env("LDFLAGS", "-lresolv")
        if has_command("brew"):
            if php80 and "-std=c++17" not in os.environ["CXXFLAGS"]:
                append_env(
                    "CXXFLAGS", "-std=c++17 -stdlib=libc++ -DU_USING_ICU_NAMESPACE=1"
                )
            if php80:
                gd = brew_prefix("gd")
                if gd and Path(gd).is_dir():
                    append_env("PKG_CONFIG_PATH", f"{gd}/lib/pkgconfig", ":")
                    common += " --with-external-gd"
            append_env("PHP_BUILD_CONFIGURE_OPTS", common)
            if not os.getenv("LDFLAGS"):
                append_env("LDFLAGS", f"-L{brew_prefix()}/lib")
            if not os.getenv("CPPFLAGS"):
                append_env("CPPFLAGS", f"-I{brew_prefix()}/include")
        else:
            append_env("PHP_BUILD_CONFIGURE_OPTS", common)
    else:
        append_env("LDFLAGS", "-Wl,--no-as-needed")
        append_env("PHP_BUILD_CONFIGURE_OPTS", common + " --without-tidy")
    if not os.environ.get("MAKE_OPTS"):
        os.environ["MAKE_OPTS"] = "-j1"
    print("Compiler configuration:")
    for key in (
        "CC",
        "CXX",
        "ac_cv_prog_CC",
        "CFLAGS",
        "CXXFLAGS",
        "LDFLAGS",
        "MAKE_OPTS",
    ):
        print(f"  {key}={os.environ.get(key, '')}")


def setup_build_concurrency() -> None:
    concurrency = os.getenv("ASDF_CONCURRENCY", "")
    if concurrency:
        os.environ["PHP_BUILD_EXTRA_MAKE_ARGUMENTS"] = f"-j{concurrency}"


def insert_patch(definition: Path, patch: str, anchor: str | None = None) -> bool:
    text = definition.read_text()
    if patch in text:
        return False
    lines = text.splitlines(keepends=True)
    if anchor:
        index = next((i for i, line in enumerate(lines) if anchor in line), None)
        if index is None:
            return False
        index += 1
    else:
        patch_indices = [i for i, line in enumerate(lines) if "patch_file" in line]
        if patch_indices:
            index = patch_indices[-1] + 1
        else:
            index = next(
                (
                    i
                    for i, line in enumerate(lines)
                    if line.startswith("install_package")
                ),
                len(lines),
            )
    lines.insert(index, f'patch_file "{patch}"\n')
    definition.write_text("".join(lines))
    return True


def patch_php_build_definitions(
    version: str, plugin_dir: Path, php_build: Path
) -> None:
    major, minor, patch = php_parts(version)
    definition = php_build / "share/php-build/definitions" / version
    patches_dir = php_build / "share/php-build/patches"
    patches_dir.mkdir(parents=True, exist_ok=True)
    groups: list[list[tuple[str, str | None]]] = []
    if major == 7 and minor == 4:
        groups.append(
            [
                ("php-7.4-libxml2-2.12.patch", None),
                ("php-7.4-icu-74-compat.patch", None),
                ("php-7.4-libxml2-attribute-unused.patch", None),
                ("php-8.0-bcmath-knr-to-ansi.patch", None),
                ("php-8.0-intl-knr-to-ansi.patch", None),
                ("php-8.0-pcntl-function-pointer-type.patch", None),
                ("php-8.0-scanf-function-pointer-call.patch", None),
                ("php-8.0-sha1-knr-to-ansi.patch", None),
                ("php-7.4-gd-function-pointer-types.patch", None),
            ]
        )
    if major == 8 and minor == 0 and patch < 20:
        groups.append(
            [
                (
                    "php-8.0-libxml2-2.12-compat.patch",
                    "php-8.0-support-openssl-3.patch",
                ),
                ("php-8.0-icu-74-compat.patch", "php-8.0-libxml2-2.12-compat.patch"),
                ("php-8.0-intl-cxx17.patch", "php-8.0-icu-74-compat.patch"),
                ("php-8.0-libxml2-const-handler.patch", "php-8.0-intl-cxx17.patch"),
                (
                    "php-8.0-libxml2-attribute-unused.patch",
                    "php-8.0-libxml2-const-handler.patch",
                ),
                (
                    "php-8.0-bcmath-knr-to-ansi.patch",
                    "php-8.0-libxml2-attribute-unused.patch",
                ),
                (
                    "php-8.0-gd-function-pointer-types.patch",
                    "php-8.0-bcmath-knr-to-ansi.patch",
                ),
                (
                    "php-8.0-intl-knr-to-ansi.patch",
                    "php-8.0-gd-function-pointer-types.patch",
                ),
                (
                    "php-8.0-pcntl-function-pointer-type.patch",
                    "php-8.0-intl-knr-to-ansi.patch",
                ),
                (
                    "php-8.0-scanf-function-pointer-call.patch",
                    "php-8.0-pcntl-function-pointer-type.patch",
                ),
                (
                    "php-8.0-sha1-knr-to-ansi.patch",
                    "php-8.0-scanf-function-pointer-call.patch",
                ),
            ]
        )
    for entries in groups:
        for name, anchor in entries:
            source = plugin_dir / "patches" / name
            if source.is_file():
                shutil.copy2(source, patches_dir / name)
            if definition.is_file() and insert_patch(definition, name, anchor):
                print(f"Added {name} to PHP {version} definition")
    if major == 7 and minor == 4 and on_macos() and definition.is_file():
        lines = definition.read_text().splitlines(keepends=True)
        updated = [line for line in lines if not line.startswith("install_xdebug ")]
        if len(updated) != len(lines):
            definition.write_text("".join(updated))
            print(
                f"Skipping xdebug for PHP {version} on macOS (xdebug 3.1.6 does not compile with Clang 17)"
            )


def php_has_extension(php: Path, extension: str) -> bool:
    result = run(
        str(php),
        "-r",
        "exit(extension_loaded($argv[1]) ? 0 : 1);",
        extension,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def install_composer(install_path: Path) -> bool:
    bin_path = install_path / "bin"
    php = bin_path / "php"
    with tempfile.TemporaryDirectory(prefix="asdf-php-composer-") as temporary:
        temp_dir = Path(temporary)
        print("=== Composer Installation Debug ===")
        print(f"PHP binary: {php}\nTemp directory: {temp_dir}")
        if not php_has_extension(php, "openssl"):
            print(
                "⚠ PHP OpenSSL extension not available - required for Composer download"
            )
            return False
        if not php_has_extension(php, "curl"):
            print("⚠ PHP curl extension not available - using fallback download method")
        signature = run(
            "curl",
            "-sL",
            "https://composer.github.io/installer.sig",
            check=False,
            capture=True,
            stderr=subprocess.STDOUT,
        ).stdout.strip()
        if not signature:
            print(
                "⚠ Could not fetch Composer installer signature\n⚠ Skipping signature verification due to network issues"
            )
        else:
            print(f"✓ Fetched Composer installer signature: {signature[:20]}...")
        print("Downloading Composer installer...")
        downloaded = (
            run(
                str(php),
                "-r",
                "copy('https://getcomposer.org/installer', 'composer-setup.php');",
                check=False,
                cwd=temp_dir,
                stderr=subprocess.DEVNULL,
            ).returncode
            == 0
        )
        if not downloaded and has_command("curl"):
            downloaded = (
                run(
                    "curl",
                    "-sL",
                    "https://getcomposer.org/installer",
                    "-o",
                    "composer-setup.php",
                    check=False,
                    cwd=temp_dir,
                ).returncode
                == 0
            )
        if not downloaded and has_command("wget"):
            downloaded = (
                run(
                    "wget",
                    "-q",
                    "https://getcomposer.org/installer",
                    "-O",
                    "composer-setup.php",
                    check=False,
                    cwd=temp_dir,
                ).returncode
                == 0
            )
        installer = temp_dir / "composer-setup.php"
        if not downloaded or not installer.is_file():
            print("⚠ Could not download Composer installer with any method")
            return False
        print(f"✓ Composer installer downloaded ({installer.stat().st_size} bytes)")
        if signature:
            result = run(
                str(php),
                "-r",
                "if (hash_file('sha384', 'composer-setup.php') === $argv[1]) { echo 'OK'; } else { echo 'FAIL'; }",
                signature,
                check=False,
                capture=True,
                cwd=temp_dir,
                stderr=subprocess.DEVNULL,
            )
            if result.stdout != "OK":
                print(
                    "⚠ Composer installer signature verification failed\n⚠ Continuing anyway due to CI environment"
                )
            else:
                print("✓ Signature verification passed")
        print("Installing Composer...")
        if (
            run(
                str(php),
                str(installer),
                f"--install-dir={bin_path}",
                "--filename=composer",
                check=False,
                cwd=temp_dir,
            ).returncode
            != 0
        ):
            print("⚠ Composer installation failed")
            return False
    composer = bin_path / "composer"
    if composer.is_file() and os.access(composer, os.X_OK):
        result = run(
            str(php),
            str(composer),
            "--version",
            check=False,
            capture=True,
            stderr=subprocess.DEVNULL,
        )
        print(f"✓ Composer verified: {result.stdout.strip() or 'unknown'}")
        return True
    print(f"⚠ Composer binary not found after installation\nContents of {bin_path}:")
    try:
        print("\n".join(path.name for path in bin_path.iterdir()))
    except OSError:
        print("Directory not accessible")
    return False


def install_xdebug(install_path: Path) -> bool:
    pecl = install_path / "bin/pecl"
    if not pecl.is_file():
        print("⚠ PECL not found")
        return False
    result = run(
        str(pecl),
        "install",
        "xdebug",
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode:
        print("⚠ Xdebug installation failed")
        return False
    with (install_path / "conf.d/xdebug.ini").open("a") as config:
        config.write("zend_extension=xdebug.so\nxdebug.mode=debug\n")
    print("✓ Xdebug installed")
    return True


def main(plugin_dir: Path) -> int:
    php_build_root = plugin_dir / "vendor/php-build"
    php_build = php_build_root / "bin/php-build"
    if not php_build.is_file():
        print("php-build not found, attempting to initialize submodule...")
        if (plugin_dir / ".git").exists():
            run(
                "git",
                "-C",
                str(plugin_dir),
                "submodule",
                "update",
                "--init",
                "--recursive",
                "vendor/php-build",
                check=False,
            )
        if not php_build.is_file():
            print(
                f"Error: php-build not found at {php_build_root}\n\nThis plugin requires php-build to be available.\n\nIf you cloned this plugin, run:\n  cd {plugin_dir}\n  git submodule update --init --recursive\n",
                file=sys.stderr,
            )
            return 1
    os.environ["PATH"] = f"{php_build_root / 'bin'}:{os.environ.get('PATH', '')}"
    version = os.environ.get("ASDF_INSTALL_VERSION")
    install_path_value = os.environ.get("ASDF_INSTALL_PATH")
    if not version or not install_path_value:
        print("ASDF_INSTALL_VERSION and ASDF_INSTALL_PATH must be set", file=sys.stderr)
        return 2
    if version == "latest":
        version = run(
            str(plugin_dir / "bin/latest-stable"), capture=True
        ).stdout.strip()
        print(f"Resolved 'latest' to version {version}")
    install_path = Path(install_path_value)
    try:
        setup_macos_dependencies()
        setup_optional_extensions()
        configure_openssl11(version, plugin_dir)
        setup_openssl_pin()
        setup_compiler_for_old_php(version)
        if not os.getenv("PHP_BUILD_XDEBUG_ENABLE"):
            os.environ["PHP_BUILD_XDEBUG_ENABLE"] = "off"
        if os.getenv("PHP_CONFIGURE_OPTIONS"):
            append_env("PHP_BUILD_CONFIGURE_OPTS", os.environ["PHP_CONFIGURE_OPTIONS"])
        if os.getenv("PHP_WITHOUT_PEAR", "no") != "no":
            append_env("PHP_BUILD_CONFIGURE_OPTS", "--without-pear")
        setup_build_concurrency()
        patch_php_build_definitions(version, plugin_dir, php_build_root)
        sanitize_cxxflags_for_modern_php(version)
        print(f"Building PHP {version}...")
        run(str(php_build), version, install_path_value)
        print(f"✓ PHP {version} built successfully")
        print("Installing Composer...")
        print(
            "✓ Composer installed"
            if install_composer(install_path)
            else "⚠ Composer installation failed"
        )
        conf = install_path / "conf.d"
        conf.mkdir(parents=True, exist_ok=True)
        php_ini = conf / "php.ini"
        if not php_ini.exists():
            php_ini.write_text("# Add custom PHP configuration here\n")
        if os.getenv("PHP_WITH_XDEBUG", "no") != "no":
            print("Installing Xdebug...")
            install_xdebug(install_path)
        print(f"✓ PHP {version} installed at: {install_path}")
        return 0
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as error:
        print(f"asdf-php: {error}", file=sys.stderr)
        return 1
