#!/usr/bin/env bats

# Integration tests for PHP installation with real-world scenarios

setup() {
  export PLUGIN_DIR="${BATS_TEST_DIRNAME}/.."
  export TEST_TEMP_DIR="$(mktemp -d)"
  export ASDF_INSTALL_VERSION="8.5.4"
  export ASDF_INSTALL_PATH="${TEST_TEMP_DIR}/install"

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

@test "PHP 8.5.4 installation should include bzip2 configuration on macOS" {
  export OSTYPE="darwin23.0"
  unset PHP_BUILD_CONFIGURE_OPTS

  setup_macos_dependencies "8.5.4"

  [[ "${PHP_BUILD_CONFIGURE_OPTS}" == *"--with-bz2=${TEST_TEMP_DIR}/opt/bzip2"* ]]
}

@test "PHP 8.4.3 installation should include bzip2 configuration on macOS" {
  export OSTYPE="darwin23.0"
  unset PHP_BUILD_CONFIGURE_OPTS

  setup_macos_dependencies "8.4.3"

  [[ "${PHP_BUILD_CONFIGURE_OPTS}" == *"--with-bz2=${TEST_TEMP_DIR}/opt/bzip2"* ]]
}

@test "PHP 8.3.15 installation should include bzip2 configuration on macOS" {
  export OSTYPE="darwin23.0"
  unset PHP_BUILD_CONFIGURE_OPTS

  setup_macos_dependencies "8.3.15"

  [[ "${PHP_BUILD_CONFIGURE_OPTS}" == *"--with-bz2=${TEST_TEMP_DIR}/opt/bzip2"* ]]
}

@test "PHP 8.2.28 installation should include bzip2 configuration on macOS" {
  export OSTYPE="darwin23.0"
  unset PHP_BUILD_CONFIGURE_OPTS

  setup_macos_dependencies "8.2.28"

  [[ "${PHP_BUILD_CONFIGURE_OPTS}" == *"--with-bz2=${TEST_TEMP_DIR}/opt/bzip2"* ]]
}

@test "PHP 8.1.31 installation should include bzip2 configuration on macOS" {
  export OSTYPE="darwin23.0"
  unset PHP_BUILD_CONFIGURE_OPTS

  setup_macos_dependencies "8.1.31"

  [[ "${PHP_BUILD_CONFIGURE_OPTS}" == *"--with-bz2=${TEST_TEMP_DIR}/opt/bzip2"* ]]
}

@test "PHP 8.0.30 installation should include bzip2 configuration on macOS" {
  export OSTYPE="darwin23.0"
  unset PHP_BUILD_CONFIGURE_OPTS

  setup_macos_dependencies "8.0.30"

  [[ "${PHP_BUILD_CONFIGURE_OPTS}" == *"--with-bz2=${TEST_TEMP_DIR}/opt/bzip2"* ]]
}

@test "PHP 7.4.33 installation should include bzip2 configuration on macOS" {
  export OSTYPE="darwin23.0"
  unset PHP_BUILD_CONFIGURE_OPTS

  setup_macos_dependencies "7.4.33"

  [[ "${PHP_BUILD_CONFIGURE_OPTS}" == *"--with-bz2=${TEST_TEMP_DIR}/opt/bzip2"* ]]
}

@test "configuration should include both LDFLAGS and CPPFLAGS for Homebrew libraries" {
  export OSTYPE="darwin23.0"
  unset LDFLAGS
  unset CPPFLAGS

  setup_macos_dependencies "8.5.4"

  [[ "${LDFLAGS}" == *"-L${TEST_TEMP_DIR}/opt/lib"* ]]
  [[ "${CPPFLAGS}" == *"-I${TEST_TEMP_DIR}/opt/include"* ]]
}

@test "should configure both bzip2 and libiconv on macOS" {
  export OSTYPE="darwin23.0"
  unset PHP_BUILD_CONFIGURE_OPTS

  setup_macos_dependencies "8.5.4"

  [[ "${PHP_BUILD_CONFIGURE_OPTS}" == *"--with-bz2=${TEST_TEMP_DIR}/opt/bzip2"* ]]
  [[ "${PHP_BUILD_CONFIGURE_OPTS}" == *"--with-iconv=${TEST_TEMP_DIR}/opt/libiconv"* ]]
}

@test "should not configure brew paths on Linux" {
  export OSTYPE="linux-gnu"
  unset PHP_BUILD_CONFIGURE_OPTS

  setup_macos_dependencies "8.5.4"

  [[ -z "${PHP_BUILD_CONFIGURE_OPTS}" ]] || [[ "${PHP_BUILD_CONFIGURE_OPTS}" != *"--with-bz2="* ]]
}

@test "should not fail when brew is not available on macOS" {
  export OSTYPE="darwin23.0"
  export PATH="/usr/bin:/bin"
  unset PHP_BUILD_CONFIGURE_OPTS

  run setup_macos_dependencies "8.5.4"

  [ "$status" -eq 0 ]
}

@test "should append to existing configuration options" {
  export OSTYPE="darwin23.0"
  export PHP_BUILD_CONFIGURE_OPTS="--enable-mbstring --with-curl"

  setup_macos_dependencies "8.5.4"

  [[ "${PHP_BUILD_CONFIGURE_OPTS}" == *"--enable-mbstring"* ]]
  [[ "${PHP_BUILD_CONFIGURE_OPTS}" == *"--with-curl"* ]]
  [[ "${PHP_BUILD_CONFIGURE_OPTS}" == *"--with-bz2=${TEST_TEMP_DIR}/opt/bzip2"* ]]
  [[ "${PHP_BUILD_CONFIGURE_OPTS}" == *"--with-iconv=${TEST_TEMP_DIR}/opt/libiconv"* ]]
}

@test "should append to existing LDFLAGS" {
  export OSTYPE="darwin23.0"
  export LDFLAGS="-L/custom/lib -lz"

  setup_macos_dependencies "8.5.4"

  [[ "${LDFLAGS}" == *"-L/custom/lib"* ]]
  [[ "${LDFLAGS}" == *"-lz"* ]]
  [[ "${LDFLAGS}" == *"-L${TEST_TEMP_DIR}/opt/lib"* ]]
}

@test "should append to existing CPPFLAGS" {
  export OSTYPE="darwin23.0"
  export CPPFLAGS="-I/custom/include -DCUSTOM_FLAG"

  setup_macos_dependencies "8.5.4"

  [[ "${CPPFLAGS}" == *"-I/custom/include"* ]]
  [[ "${CPPFLAGS}" == *"-DCUSTOM_FLAG"* ]]
  [[ "${CPPFLAGS}" == *"-I${TEST_TEMP_DIR}/opt/include"* ]]
}

@test "should skip bzip2 configuration if directory does not exist" {
  export OSTYPE="darwin23.0"
  unset PHP_BUILD_CONFIGURE_OPTS

  # Remove both opt and Cellar paths so resolve_brew_package_prefix finds nothing valid
  rm -rf "${TEST_TEMP_DIR}/opt/bzip2"
  rm -rf "${TEST_TEMP_DIR}/cellar/bzip2"

  setup_macos_dependencies "8.5.4"

  [[ -z "${PHP_BUILD_CONFIGURE_OPTS}" ]] || [[ "${PHP_BUILD_CONFIGURE_OPTS}" != *"--with-bz2="* ]]
}

@test "should skip libiconv configuration if directory does not exist" {
  export OSTYPE="darwin23.0"
  unset PHP_BUILD_CONFIGURE_OPTS

  # Remove both opt and Cellar paths so resolve_brew_package_prefix finds nothing valid
  rm -rf "${TEST_TEMP_DIR}/opt/libiconv"
  rm -rf "${TEST_TEMP_DIR}/cellar/libiconv"

  setup_macos_dependencies "8.5.4"

  [[ -z "${PHP_BUILD_CONFIGURE_OPTS}" ]] || [[ "${PHP_BUILD_CONFIGURE_OPTS}" != *"--with-iconv="* ]]
}

@test "should handle version with RC suffix" {
  export OSTYPE="darwin23.0"
  unset PHP_BUILD_CONFIGURE_OPTS

  setup_macos_dependencies "8.5.0RC1"

  [[ "${PHP_BUILD_CONFIGURE_OPTS}" == *"--with-bz2=${TEST_TEMP_DIR}/opt/bzip2"* ]]
}

@test "should handle version with beta suffix" {
  export OSTYPE="darwin23.0"
  unset PHP_BUILD_CONFIGURE_OPTS

  setup_macos_dependencies "8.5.0beta2"

  [[ "${PHP_BUILD_CONFIGURE_OPTS}" == *"--with-bz2=${TEST_TEMP_DIR}/opt/bzip2"* ]]
}

@test "should handle version with alpha suffix" {
  export OSTYPE="darwin23.0"
  unset PHP_BUILD_CONFIGURE_OPTS

  setup_macos_dependencies "8.6.0alpha1"

  [[ "${PHP_BUILD_CONFIGURE_OPTS}" == *"--with-bz2=${TEST_TEMP_DIR}/opt/bzip2"* ]]
}
