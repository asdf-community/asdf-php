#!/usr/bin/env bats
# shellcheck disable=SC2292 # Bats assertions are not Bash test syntax.
bats_require_minimum_version 1.7.0

# These tests run bin/install itself. A fake python3 stands in for the asdf
# Python shim: it overwrites ASDF_INSTALL_* like the shim does, then records
# what it received so each test can check the values bin/install forwarded.

setup() {
  export TEST_TEMP_DIR="${BATS_TEST_TMPDIR}"
  export MOCK_PYTHON_LOG="${TEST_TEMP_DIR}/python.log"

  mkdir -p "${TEST_TEMP_DIR}/mock-bin"
  cat >"${TEST_TEMP_DIR}/mock-bin/python3" <<'EOF'
#!/usr/bin/env bash
# bin/install asks for the version first; answer without logging it.
if [[ "$1" == "-c" ]]; then
  exit "${MOCK_PYTHON_VERSION_CHECK:-0}"
fi
if [[ "$1" == "--version" ]]; then
  printf 'Python %s\n' "${MOCK_PYTHON_VERSION:-3.14.6}"
  exit 0
fi
# Mimic the asdf Python shim: it sets the install variables for Python.
export ASDF_INSTALL_VERSION=3.14.6
export ASDF_INSTALL_PATH=/shim/installs/python/3.14.6
{
  printf 'ASDF_INSTALL_VERSION=%s\n' "${ASDF_INSTALL_VERSION-<unset>}"
  printf 'ASDF_INSTALL_PATH=%s\n' "${ASDF_INSTALL_PATH-<unset>}"
  printf 'ASDF_PHP_INSTALL_VERSION=%s\n' "${ASDF_PHP_INSTALL_VERSION-<unset>}"
  printf 'ASDF_PHP_INSTALL_PATH=%s\n' "${ASDF_PHP_INSTALL_PATH-<unset>}"
  printf 'ARGS=%s\n' "$*"
} >>"${MOCK_PYTHON_LOG}"
exit 0
EOF
  chmod +x "${TEST_TEMP_DIR}/mock-bin/python3"
  export PATH="${TEST_TEMP_DIR}/mock-bin:${PATH}"
}

@test "copies the asdf PHP values to ASDF_PHP names before Python starts" {
  run env ASDF_INSTALL_VERSION=8.5.12 ASDF_INSTALL_PATH=/x/php/8.5.12 \
    "${BATS_TEST_DIRNAME}/../bin/install"

  [ "${status}" -eq 0 ]
  grep -qx 'ASDF_PHP_INSTALL_VERSION=8.5.12' "${MOCK_PYTHON_LOG}"
  grep -qx 'ASDF_PHP_INSTALL_PATH=/x/php/8.5.12' "${MOCK_PYTHON_LOG}"
}

@test "the shim's ASDF_INSTALL values do not reach the ASDF_PHP names" {
  run env ASDF_INSTALL_VERSION=8.5.12 ASDF_INSTALL_PATH=/x/php/8.5.12 \
    "${BATS_TEST_DIRNAME}/../bin/install"

  [ "${status}" -eq 0 ]
  grep -qx 'ASDF_INSTALL_VERSION=3.14.6' "${MOCK_PYTHON_LOG}"
  grep -qx 'ASDF_PHP_INSTALL_VERSION=8.5.12' "${MOCK_PYTHON_LOG}"
  run grep -q 'ASDF_PHP_INSTALL_VERSION=3.14.6' "${MOCK_PYTHON_LOG}"
  [ "${status}" -eq 1 ]
}

@test "passes command-line arguments through to Python" {
  run "${BATS_TEST_DIRNAME}/../bin/install" --help

  [ "${status}" -eq 0 ]
  grep -qE 'ARGS=.*install\.py --help$' "${MOCK_PYTHON_LOG}"
}

@test "forwards empty values when asdf sets no install variables" {
  run env -u ASDF_INSTALL_VERSION -u ASDF_INSTALL_PATH \
    "${BATS_TEST_DIRNAME}/../bin/install"

  [ "${status}" -eq 0 ]
  grep -qx 'ASDF_PHP_INSTALL_VERSION=' "${MOCK_PYTHON_LOG}"
  grep -qx 'ASDF_PHP_INSTALL_PATH=' "${MOCK_PYTHON_LOG}"
}

@test "stops with a clear message when Python is older than 3.9" {
  run -1 env MOCK_PYTHON_VERSION_CHECK=1 MOCK_PYTHON_VERSION=3.6.8 \
    "${BATS_TEST_DIRNAME}/../bin/install"

  [ "${output}" = "install: requires Python 3.9 or newer (found Python 3.6.8)" ]
}

@test "does not start install.py when Python is too old" {
  run -1 env MOCK_PYTHON_VERSION_CHECK=1 "${BATS_TEST_DIRNAME}/../bin/install"

  [ ! -e "${MOCK_PYTHON_LOG}" ]
}
