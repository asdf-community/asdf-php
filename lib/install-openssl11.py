#!/usr/bin/env python3
"""Build OpenSSL 1.1 for PHP versions that need the legacy ABI."""

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request


VERSION = "1.1.1w"
URL = f"https://www.openssl.org/source/openssl-{VERSION}.tar.gz"


def run(*args, cwd=None, check=True, **kwargs):
    return subprocess.run(args, cwd=cwd, check=check, text=True, **kwargs)


def download(url, destination):
    request = urllib.request.Request(url, headers={"User-Agent": "asdf-php"})
    with urllib.request.urlopen(request, timeout=60) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)


def checksum(expected, archive):
    if not expected:
        return None
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    return digest.lower() == expected.lower()


def build_jobs():
    for command in (("nproc",), ("sysctl", "-n", "hw.ncpu")):
        if shutil.which(command[0]):
            result = run(
                *command, check=False, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
            )
            try:
                jobs = int(result.stdout.strip())
            except ValueError:
                continue
            if result.returncode == 0 and jobs > 0:
                return jobs
    return 4


def main(argv):
    if sys.version_info < (3, 9):
        print("install-openssl11.py requires Python 3.9 or newer", file=sys.stderr)
        return 1
    if len(argv) > 1:
        print(f"Usage: {Path(sys.argv[0]).name} [--auto|--help]", file=sys.stderr)
        return 2
    if argv and argv[0] in ("-h", "--help"):
        print(f"OpenSSL {VERSION} Installation Script\n\nUsage: {Path(sys.argv[0]).name} [--auto|--help]\n\n--auto skips the confirmation prompt.")
        return 0
    if argv and argv[0] != "--auto":
        print(f"Usage: {Path(sys.argv[0]).name} [--auto|--help]", file=sys.stderr)
        return 2
    auto = bool(argv)
    prefix = Path(os.getenv("INSTALL_PREFIX", str(Path.home() / ".local/openssl-1.1"))).expanduser()
    binary = prefix / "bin/openssl"
    if binary.is_file():
        result = run(
            str(binary),
            "version",
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode == 0:
            version = result.stdout.split()[1]
            print(f"OpenSSL 1.1 already installed: {version} at {prefix}")
            print(f'  export PKG_CONFIG_PATH="{prefix}/lib/pkgconfig:$PKG_CONFIG_PATH"')
            print(f'  export PHP_BUILD_CONFIGURE_OPTS="--with-openssl={prefix}"')
            print(f'  export LD_LIBRARY_PATH="{prefix}/lib:$LD_LIBRARY_PATH"')
            return 0

    missing = [name for name in ("gcc", "make", "perl") if shutil.which(name) is None]
    if missing:
        print(f"Missing dependencies: {', '.join(missing)}", file=sys.stderr)
        if shutil.which("apt-get"):
            print("  sudo apt-get install -y build-essential perl")
        elif shutil.which("yum"):
            print("  sudo yum install -y gcc make perl-core")
        return 1
    if not auto and sys.stdin.isatty() and not input(f"Install OpenSSL {VERSION} to {prefix}? [y/N] ").lower().startswith("y"):
        return 0
    if not auto and not sys.stdin.isatty():
        print("Use --auto when running without a terminal.", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory(prefix="openssl-1.1-build-") as temporary:
        work = Path(temporary)
        archive = work / "openssl.tar.gz"
        print(f"Downloading OpenSSL {VERSION}...")
        try:
            download(URL, archive)
        except OSError as error:
            print(f"Download failed: {error}", file=sys.stderr)
            return 1
        expected = os.getenv("OPENSSL_SHA256", "")
        if not expected:
            print("Attempting to retrieve official checksum...")
            for url in (URL + ".sha256", f"https://github.com/openssl/openssl/releases/download/OpenSSL_{VERSION.replace('.', '_')}/openssl-{VERSION}.tar.gz.sha256"):
                try:
                    with urllib.request.urlopen(url, timeout=20) as response:
                        expected = response.read().decode().split()[0]
                    if len(expected) == 64:
                        print(f"Retrieved checksum from: {url}")
                        break
                    expected = ""
                except (OSError, IndexError):
                    expected = ""
        if len(expected) != 64:
            expected = ""
        if expected:
            if checksum(expected, archive) is False:
                print("SHA256 checksum verification failed; archive may be corrupted or tampered with.", file=sys.stderr)
                return 1
            print("✓ Download integrity verified")
        else:
            print("⚠ Could not retrieve official SHA256 checksum; proceeding without integrity check.")
        print("Extracting and configuring...")
        with tarfile.open(archive, "r:gz") as tar:
            root = work.resolve()
            for member in tar.getmembers():
                target = (work / member.name).resolve()
                if os.path.commonpath((str(root), str(target))) != str(root):
                    raise RuntimeError(f"unsafe path in OpenSSL archive: {member.name}")
                if member.issym() or member.islnk():
                    link_target = (target.parent / member.linkname).resolve()
                    if os.path.commonpath((str(root), str(link_target))) != str(root):
                        raise RuntimeError(f"unsafe link in OpenSSL archive: {member.name}")
            tar.extractall(work)
        source = work / f"openssl-{VERSION}"
        jobs = build_jobs()
        run("./config", f"--prefix={prefix}", f"--openssldir={prefix}", "shared", "zlib", "no-tests", cwd=source, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"Compiling with {jobs} cores (2-5 minutes)...")
        run("make", f"-j{jobs}", cwd=source, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"Installing to {prefix}...")
        prefix.mkdir(parents=True, exist_ok=True)
        run("make", "install_sw", "install_ssldirs", cwd=source, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not binary.is_file():
        print("Installation failed", file=sys.stderr)
        return 1
    result = run(
        str(binary),
        "version",
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode:
        print("OpenSSL installed but version check failed", file=sys.stderr)
        return 1
    print(f"✓ OpenSSL {result.stdout.split()[1]} installed successfully")
    if not auto:
        print(f'Add to your shell profile: export PKG_CONFIG_PATH="{prefix}/lib/pkgconfig:$PKG_CONFIG_PATH"')
        print(f'export PHP_BUILD_CONFIGURE_OPTS="--with-openssl={prefix}"')
        print(f'export LD_LIBRARY_PATH="{prefix}/lib:$LD_LIBRARY_PATH"')
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"install-openssl11.py: {error}", file=sys.stderr)
        raise SystemExit(1)
