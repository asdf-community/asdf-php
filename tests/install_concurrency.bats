#!/usr/bin/env bats

# Tests for ASDF_CONCURRENCY pass-through to php-build, which does not read
# ASDF_CONCURRENCY natively and requires explicit translation to make arguments

setup() {
  export PLUGIN_DIR="${BATS_TEST_DIRNAME}/.."
  export TEST_TEMP_DIR="$(mktemp -d)"

  # Extract and source only the target function to avoid install script side effects
  sed -n '/^# php-build does not read ASDF_CONCURRENCY/,/^}$/p' \
    "${PLUGIN_DIR}/bin/install" > "${TEST_TEMP_DIR}/function.sh"
  source "${TEST_TEMP_DIR}/function.sh"
}

teardown() {
  unset PHP_BUILD_EXTRA_MAKE_ARGUMENTS
  unset ASDF_CONCURRENCY
  rm -rf "${TEST_TEMP_DIR}"
}

@test "should set PHP_BUILD_EXTRA_MAKE_ARGUMENTS to -j8 when ASDF_CONCURRENCY is 8" {
  export ASDF_CONCURRENCY=8

  setup_build_concurrency

  [ "${PHP_BUILD_EXTRA_MAKE_ARGUMENTS}" = "-j8" ]
}

@test "should set PHP_BUILD_EXTRA_MAKE_ARGUMENTS to -j4 when ASDF_CONCURRENCY is 4" {
  export ASDF_CONCURRENCY=4

  setup_build_concurrency

  [ "${PHP_BUILD_EXTRA_MAKE_ARGUMENTS}" = "-j4" ]
}

@test "should set PHP_BUILD_EXTRA_MAKE_ARGUMENTS to -j1 when ASDF_CONCURRENCY is 1" {
  export ASDF_CONCURRENCY=1

  setup_build_concurrency

  [ "${PHP_BUILD_EXTRA_MAKE_ARGUMENTS}" = "-j1" ]
}

@test "should not set PHP_BUILD_EXTRA_MAKE_ARGUMENTS when ASDF_CONCURRENCY is not set" {
  unset ASDF_CONCURRENCY
  unset PHP_BUILD_EXTRA_MAKE_ARGUMENTS

  setup_build_concurrency

  [ -z "${PHP_BUILD_EXTRA_MAKE_ARGUMENTS:-}" ]
}

@test "should not set PHP_BUILD_EXTRA_MAKE_ARGUMENTS when ASDF_CONCURRENCY is empty" {
  export ASDF_CONCURRENCY=""
  unset PHP_BUILD_EXTRA_MAKE_ARGUMENTS

  setup_build_concurrency

  [ -z "${PHP_BUILD_EXTRA_MAKE_ARGUMENTS:-}" ]
}

@test "should produce a valid -j flag format that make accepts when ASDF_CONCURRENCY is set" {
  export ASDF_CONCURRENCY=8

  setup_build_concurrency

  [[ "${PHP_BUILD_EXTRA_MAKE_ARGUMENTS}" =~ ^-j[0-9]+$ ]]
}
