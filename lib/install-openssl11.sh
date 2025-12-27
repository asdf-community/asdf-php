#!/usr/bin/env bash
set -eo pipefail

OPENSSL_VERSION="1.1.1w"
INSTALL_PREFIX="${INSTALL_PREFIX:-$HOME/.local/openssl-1.1}"
TEMP_DIR="/tmp/openssl-1.1-build-$$"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check for --auto flag
AUTO_MODE=false
if [ "$1" = "--auto" ]; then
  AUTO_MODE=true
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
