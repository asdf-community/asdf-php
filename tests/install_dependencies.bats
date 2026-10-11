#!/usr/bin/env bats

# Tests for macOS dependency configuration in the install script

setup() {
  export PLUGIN_DIR="${BATS_TEST_DIRNAME}/.."
  export TEST_TEMP_DIR="$(mktemp -d)"
  export ASDF_INSTALL_VERSION="8.5.4"
  export ASDF_INSTALL_PATH="${TEST_TEMP_DIR}/install"

  # Mock brew command for macOS testing
  export MOCK_BREW_PREFIX="/usr/local/opt"
  mkdir -p "${TEST_TEMP_DIR}/bin"
  # The include subdirectory must exist so resolve_brew_package_prefix treats the
  # opt path as valid and returns it directly without falling back to the Cellar
  mkdir -p "${TEST_TEMP_DIR}/opt/bzip2/include"
  mkdir -p "${TEST_TEMP_DIR}/opt/libiconv/include"

  # The mock Cellar is isolated from the real system so tests never accidentally
  # resolve headers from a pre-existing Homebrew installation on the host machine
  mkdir -p "${TEST_TEMP_DIR}/cellar/bzip2/1.0.8/include"
  mkdir -p "${TEST_TEMP_DIR}/cellar/libiconv/1.18/include"

  cat > "${TEST_TEMP_DIR}/bin/brew" <<EOF
#!/bin/bash
if [ "\$1" = "--prefix" ]; then
  if [ "\$2" = "bzip2" ]; then
    echo "${TEST_TEMP_DIR}/opt/bzip2"
  elif [ "\$2" = "libiconv" ]; then
    echo "${TEST_TEMP_DIR}/opt/libiconv"
  else
    echo "${TEST_TEMP_DIR}/opt"
  fi
elif [ "\$1" = "--cellar" ]; then
  if [ "\$2" = "bzip2" ]; then
    echo "${TEST_TEMP_DIR}/cellar/bzip2"
  elif [ "\$2" = "libiconv" ]; then
    echo "${TEST_TEMP_DIR}/cellar/libiconv"
  fi
fi
EOF
  chmod +x "${TEST_TEMP_DIR}/bin/brew"
  export PATH="${TEST_TEMP_DIR}/bin:$PATH"

  # resolve_brew_package_prefix must be sourced before setup_macos_dependencies
  # because setup_macos_dependencies calls it at runtime
  sed -n '/^# Homebrew keg-only packages/,/^}$/p' "${PLUGIN_DIR}/bin/install" > "${TEST_TEMP_DIR}/function.sh"
  sed -n '/^# Configure macOS-specific dependencies for all PHP versions$/,/^}$/p' "${PLUGIN_DIR}/bin/install" >> "${TEST_TEMP_DIR}/function.sh"
  source "${TEST_TEMP_DIR}/function.sh"
}

teardown() {
  rm -rf "${TEST_TEMP_DIR}"
}

@test "should configure bzip2 paths on macOS for PHP 8.5.4" {
  export OSTYPE="darwin23.0"

  setup_macos_dependencies "8.5.4"

  [[ "${PHP_BUILD_CONFIGURE_OPTS}" == *"--with-bz2=${TEST_TEMP_DIR}/opt/bzip2"* ]]
}

@test "should configure bzip2 paths on macOS for PHP 8.4.0" {
  export OSTYPE="darwin23.0"

  setup_macos_dependencies "8.4.0"

  [[ "${PHP_BUILD_CONFIGURE_OPTS}" == *"--with-bz2=${TEST_TEMP_DIR}/opt/bzip2"* ]]
}

@test "should configure bzip2 paths on macOS for PHP 8.3.0" {
  export OSTYPE="darwin23.0"

  setup_macos_dependencies "8.3.0"

  [[ "${PHP_BUILD_CONFIGURE_OPTS}" == *"--with-bz2=${TEST_TEMP_DIR}/opt/bzip2"* ]]
}

@test "should configure libiconv paths on macOS for all PHP versions" {
  export OSTYPE="darwin23.0"

  setup_macos_dependencies "8.5.4"

  [[ "${PHP_BUILD_CONFIGURE_OPTS}" == *"--with-iconv=${TEST_TEMP_DIR}/opt/libiconv"* ]]
}

@test "should set LDFLAGS on macOS when brew is available" {
  export OSTYPE="darwin23.0"

  setup_macos_dependencies "8.5.4"

  [[ "${LDFLAGS}" == *"-L${TEST_TEMP_DIR}/opt/lib"* ]]
}

@test "should set CPPFLAGS on macOS when brew is available" {
  export OSTYPE="darwin23.0"

  setup_macos_dependencies "8.5.4"

  [[ "${CPPFLAGS}" == *"-I${TEST_TEMP_DIR}/opt/include"* ]]
}

@test "should not configure brew dependencies on Linux" {
  export OSTYPE="linux-gnu"

  setup_macos_dependencies "8.5.4"

  [[ "${PHP_BUILD_CONFIGURE_OPTS}" != *"--with-bz2=/usr/local"* ]]
}

@test "should handle missing brew command gracefully on macOS" {
  export OSTYPE="darwin23.0"
  export PATH="/usr/bin:/bin"

  setup_macos_dependencies "8.5.4"

  [ $? -eq 0 ]
}

@test "should preserve existing PHP_BUILD_CONFIGURE_OPTS when adding bzip2" {
  export OSTYPE="darwin23.0"
  export PHP_BUILD_CONFIGURE_OPTS="--enable-mbstring --with-curl"

  setup_macos_dependencies "8.5.4"

  [[ "${PHP_BUILD_CONFIGURE_OPTS}" == *"--enable-mbstring"* ]]
  [[ "${PHP_BUILD_CONFIGURE_OPTS}" == *"--with-curl"* ]]
  [[ "${PHP_BUILD_CONFIGURE_OPTS}" == *"--with-bz2=${TEST_TEMP_DIR}/opt/bzip2"* ]]
}

@test "should preserve existing LDFLAGS when adding brew lib path" {
  export OSTYPE="darwin23.0"
  export LDFLAGS="-L/custom/path"

  setup_macos_dependencies "8.5.4"

  [[ "${LDFLAGS}" == *"-L/custom/path"* ]]
  [[ "${LDFLAGS}" == *"-L${TEST_TEMP_DIR}/opt/lib"* ]]
}

@test "should preserve existing CPPFLAGS when adding brew include path" {
  export OSTYPE="darwin23.0"
  export CPPFLAGS="-I/custom/include"

  setup_macos_dependencies "8.5.4"

  [[ "${CPPFLAGS}" == *"-I/custom/include"* ]]
  [[ "${CPPFLAGS}" == *"-I${TEST_TEMP_DIR}/opt/include"* ]]
}

@test "should return opt prefix when include directory exists" {
  # No setup needed — the shared setup already creates opt/bzip2/include

  result=$(resolve_brew_package_prefix bzip2)

  [ "$result" = "${TEST_TEMP_DIR}/opt/bzip2" ]
}

@test "should repair the opt symlink in-place when its include directory is absent" {
  # Simulate the production failure: opt dir exists but include/ is absent because
  # Homebrew did not auto-link the keg-only package after an upgrade or reinstall
  rm -rf "${TEST_TEMP_DIR}/opt/bzip2/include"

  resolve_brew_package_prefix bzip2

  # The opt path must now resolve to the Cellar version so macOS dyld can follow
  # the library's embedded install_name which was originally set to the opt path
  [ -L "${TEST_TEMP_DIR}/opt/bzip2" ]
  [ -d "${TEST_TEMP_DIR}/opt/bzip2/include" ]
}

@test "should leave opt prefix unchanged when Cellar fallback also has no include directory" {
  # When neither opt nor Cellar has a valid include dir, leave opt as-is and let
  # the configure script decide whether to error or skip the dependency
  rm -rf "${TEST_TEMP_DIR}/opt/bzip2/include"
  rm -rf "${TEST_TEMP_DIR}/cellar/bzip2/1.0.8/include"

  result=$(resolve_brew_package_prefix bzip2)

  [ "$result" = "${TEST_TEMP_DIR}/opt/bzip2" ]
}

@test "should return empty string when brew cannot find the package" {
  cat > "${TEST_TEMP_DIR}/bin/brew" <<'EOF'
#!/bin/bash
exit 1
EOF
  chmod +x "${TEST_TEMP_DIR}/bin/brew"

  result=$(resolve_brew_package_prefix bzip2)

  [ -z "$result" ]
}
