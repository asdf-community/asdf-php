#!/usr/bin/env bats
# shellcheck disable=SC2292 # Bats assertions are not Bash test syntax.
bats_require_minimum_version 1.7.0

setup() {
  export TEST_TEMP_DIR="${BATS_TEST_TMPDIR}"
  export PLUGIN_DIR="${TEST_TEMP_DIR}/plugin"
  export MOCK_GIT_LOG="${TEST_TEMP_DIR}/git.log"
  export PINNED_PHP_BUILD_SHA="48f66c3c15eaead0ef362b5349dc85cc24195da3"
  REAL_GIT="$(command -v git)"
  export REAL_GIT

  mkdir -p "${PLUGIN_DIR}/bin" "${PLUGIN_DIR}/vendor"
  touch "${PLUGIN_DIR}/.git"
  cp "${BATS_TEST_DIRNAME}/../bin/post-plugin-add" \
    "${PLUGIN_DIR}/bin/post-plugin-add"
  mkdir -p "${TEST_TEMP_DIR}/mock-bin"

  cat >"${TEST_TEMP_DIR}/mock-bin/git" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$MOCK_GIT_LOG"
case " $* " in
  *"submodule update"*)
    if [ "${MOCK_SUBMODULE_FAIL:-no}" = yes ]; then
      exit 1
    fi
    mkdir -p "$PLUGIN_DIR/vendor/php-build/bin"
    : > "$PLUGIN_DIR/vendor/php-build/bin/php-build"
    ;;
  *"rev-parse HEAD"*)
    echo "$PINNED_PHP_BUILD_SHA"
    ;;
esac
EOF
  chmod +x "${TEST_TEMP_DIR}/mock-bin/git"
  export PATH="${TEST_TEMP_DIR}/mock-bin:${PATH}"
}

@test "php-build submodule points at the revision verified by CI" {
  run "${REAL_GIT}" -C "${BATS_TEST_DIRNAME}/.." \
    ls-files --stage vendor/php-build

  [ "${status}" -eq 0 ]
  printf '%s\n' "${output}" | grep -F -- "${PINNED_PHP_BUILD_SHA}"
  printf '%s\n' "${output}" | grep -F -- '160000'
  printf '%s\n' "${output}" | grep -F -- 'vendor/php-build'
}

@test "initializes the pinned submodule and reports its revision" {
  run "${PLUGIN_DIR}/bin/post-plugin-add"

  [ "${status}" -eq 0 ]
  printf '%s\n' "${output}" | grep -F -- "${PINNED_PHP_BUILD_SHA}"
  grep -F -- "submodule update --init --recursive vendor/php-build" \
    "${MOCK_GIT_LOG}"
  run -1 grep -F -- "Cloning php-build" <<<"${output}"
  [ "${status}" -eq 1 ]
}

@test "failed submodule setup prints a repair hint" {
  export MOCK_SUBMODULE_FAIL=yes

  run "${PLUGIN_DIR}/bin/post-plugin-add"

  [ "${status}" -ne 0 ]
  printf '%s\n' "${output}" |
    grep -F -- "git submodule update --init --recursive vendor/php-build"
  run -1 grep -F -- "Cloning php-build" <<<"${output}"
  [ "${status}" -eq 1 ]
}
