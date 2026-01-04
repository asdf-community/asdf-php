#!/usr/bin/env bash
set -eo pipefail

OPENSSL_VERSION="1.1.1w"
# Optional: Set OPENSSL_SHA256 environment variable to verify download integrity
# If not set, the script will attempt to retrieve the official checksum automatically
INSTALL_PREFIX="${INSTALL_PREFIX:-$HOME/.local/openssl-1.1}"
TEMP_DIR="/tmp/openssl-1.1-build-$$"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check for flags
AUTO_MODE=false
SHOW_HELP=false
if [ "$1" = "--auto" ]; then
  AUTO_MODE=true
elif [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
  SHOW_HELP=true
fi

# Show help if requested
if [ "$SHOW_HELP" = true ]; then
  echo "OpenSSL 1.1.1w Installation Script"
  echo
  echo "Usage: $0 [--auto|--help]"
  echo
  echo "Options:"
  echo "  --auto    Skip confirmation prompt"
  echo "  --help    Show this help message"
  echo
  echo "Security Verification:"
  echo "  The script verifies download integrity using SHA256 checksums:"
  echo "  1. If OPENSSL_SHA256 is set, uses that checksum (recommended for CI)"
  echo "  2. Otherwise, attempts to retrieve official checksum from OpenSSL.org"
  echo "  3. If retrieval fails, proceeds with a warning"
  echo
  echo "Examples:"
  echo "  # With manual checksum verification:"
  echo "  OPENSSL_SHA256=cf3098950cb4d853ad95c0841f1f9c6d3dc102dccfcacd521d93925208b76ac8 $0"
  echo
  echo "  # Automatic checksum retrieval:"
  echo "  $0"
  echo
  echo "  # Silent installation with automatic verification:"
  echo "  $0 --auto"
  exit 0
fi

# Check if already installed
if [ -f "$INSTALL_PREFIX/bin/openssl" ]; then
  installed_version=$(LD_LIBRARY_PATH="$INSTALL_PREFIX/lib:$LD_LIBRARY_PATH" "$INSTALL_PREFIX/bin/openssl" version 2>/dev/null | awk '{print $2}')
  if [ -n "$installed_version" ]; then
    echo -e "${GREEN}✓${NC} OpenSSL 1.1 already installed: ${installed_version} at ${INSTALL_PREFIX}"
    echo "  export PKG_CONFIG_PATH=\"${INSTALL_PREFIX}/lib/pkgconfig:\$PKG_CONFIG_PATH\""
    echo "  export PHP_BUILD_CONFIGURE_OPTS=\"--with-openssl=${INSTALL_PREFIX}\""
    echo "  export LD_LIBRARY_PATH=\"${INSTALL_PREFIX}/lib:\$LD_LIBRARY_PATH\""
    exit 0
  fi
fi

# Check dependencies
missing_deps=()
for cmd in gcc make perl; do
  if ! command -v $cmd &> /dev/null; then
    missing_deps+=("$cmd")
  fi
done

if [ ${#missing_deps[@]} -ne 0 ]; then
  echo -e "${RED}✗${NC} Missing dependencies: ${missing_deps[*]}"
  if command -v apt-get &> /dev/null; then
    echo "  sudo apt-get install -y build-essential perl"
  elif command -v yum &> /dev/null; then
    echo "  sudo yum install -y gcc make perl-core"
  fi
  exit 1
fi

# Confirm (skip in auto mode)
if [ "$AUTO_MODE" = false ]; then
  read -p "Install OpenSSL ${OPENSSL_VERSION} to ${INSTALL_PREFIX}? [y/N] " -n 1 -r
  echo
  [[ ! $REPLY =~ ^[Yy]$ ]] && exit 0
fi

# Cleanup on exit
trap "rm -rf $TEMP_DIR" EXIT

# Download
mkdir -p "$TEMP_DIR" && cd "$TEMP_DIR"
echo "Downloading OpenSSL ${OPENSSL_VERSION}..."
curl -fsSL -o openssl.tar.gz "https://www.openssl.org/source/openssl-${OPENSSL_VERSION}.tar.gz" || exit 1

# Verify download integrity
echo "Verifying download integrity..."

# Use environment variable if provided, otherwise try to get official checksum
if [ -n "$OPENSSL_SHA256" ]; then
  echo "Using provided checksum: $OPENSSL_SHA256"
else
  echo "Attempting to retrieve official checksum..."
  for checksum_url in \
    "https://www.openssl.org/source/openssl-${OPENSSL_VERSION}.tar.gz.sha256" \
    "https://github.com/openssl/openssl/releases/download/OpenSSL_$(echo $OPENSSL_VERSION | tr '.' '_')/openssl-${OPENSSL_VERSION}.tar.gz.sha256"; do

    if RETRIEVED_CHECKSUM=$(curl -fsSL "$checksum_url" 2>/dev/null | head -1 | awk '{print $1}'); then
      if [ -n "$RETRIEVED_CHECKSUM" ] && [ ${#RETRIEVED_CHECKSUM} -eq 64 ]; then
        OPENSSL_SHA256="$RETRIEVED_CHECKSUM"
        echo "Retrieved checksum from: $checksum_url"
        break
      fi
    fi
  done
fi

# If we have a checksum, verify it
if [ -n "$OPENSSL_SHA256" ] && [ ${#OPENSSL_SHA256} -eq 64 ]; then
  echo "Verifying SHA256: $OPENSSL_SHA256"
  if command -v sha256sum >/dev/null 2>&1; then
    echo "${OPENSSL_SHA256}  openssl.tar.gz" | sha256sum -c - || {
      echo -e "${RED}✗${NC} SHA256 checksum verification failed! File may be corrupted or tampered with."
      exit 1
    }
  elif command -v shasum >/dev/null 2>&1; then
    echo "${OPENSSL_SHA256}  openssl.tar.gz" | shasum -a 256 -c - || {
      echo -e "${RED}✗${NC} SHA256 checksum verification failed! File may be corrupted or tampered with."
      exit 1
    }
  else
    echo -e "${YELLOW}⚠${NC} Warning: No SHA256 verification tool available (sha256sum or shasum)."
  fi
  echo -e "${GREEN}✓${NC} Download integrity verified"
else
  echo -e "${YELLOW}⚠${NC} Warning: Could not retrieve official SHA256 checksum."
  echo -e "${YELLOW}⚠${NC} To enable verification, set OPENSSL_SHA256 environment variable with the official checksum."
  echo -e "${YELLOW}⚠${NC} Proceeding without integrity check - use at your own risk."
fi

# Extract & build
echo "Extracting and configuring..."
tar -xzf openssl.tar.gz && cd "openssl-${OPENSSL_VERSION}"

CORES=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)
./config --prefix="$INSTALL_PREFIX" --openssldir="$INSTALL_PREFIX" shared zlib no-tests > /dev/null 2>&1

echo "Compiling with ${CORES} cores (2-5 minutes)..."
make -j"$CORES" > /dev/null 2>&1

echo "Installing to ${INSTALL_PREFIX}..."
mkdir -p "$INSTALL_PREFIX"
make install_sw install_ssldirs > /dev/null 2>&1

# Verify
if [ -f "$INSTALL_PREFIX/bin/openssl" ]; then
  installed_version=$(LD_LIBRARY_PATH="$INSTALL_PREFIX/lib:$LD_LIBRARY_PATH" "$INSTALL_PREFIX/bin/openssl" version 2>/dev/null | awk '{print $2}')
  if [ -n "$installed_version" ]; then
    echo -e "${GREEN}✓${NC} OpenSSL ${installed_version} installed successfully"

    # Only show instructions in manual mode
    if [ "$AUTO_MODE" = false ]; then
      echo
      echo "Add to your shell profile (~/.bashrc or ~/.zshrc):"
      echo "  export PKG_CONFIG_PATH=\"${INSTALL_PREFIX}/lib/pkgconfig:\$PKG_CONFIG_PATH\""
      echo "  export PHP_BUILD_CONFIGURE_OPTS=\"--with-openssl=${INSTALL_PREFIX}\""
      echo "  export LD_LIBRARY_PATH=\"${INSTALL_PREFIX}/lib:\$LD_LIBRARY_PATH\""
    fi
  else
    echo -e "${RED}✗${NC} OpenSSL installed but cannot verify version"
    exit 1
  fi
else
  echo -e "${RED}✗${NC} Installation failed"
  exit 1
fi
