#!/usr/bin/env bats

setup() {
  export TEST_TEMP_DIR="$(mktemp -d)"
  export PLUGIN_DIR="${TEST_TEMP_DIR}/plugin"
  export MOCK_GIT_LOG="${TEST_TEMP_DIR}/git.log"
  export PINNED_PHP_BUILD_SHA="2180bc5462729543639c928e5da05c90b56b9f7c"
  export REAL_GIT="$(command -v git)"

  mkdir -p "${PLUGIN_DIR}/bin" "${PLUGIN_DIR}/vendor"
  touch "${PLUGIN_DIR}/.git"
  cp "${BATS_TEST_DIRNAME}/../bin/post-plugin-add" "${PLUGIN_DIR}/bin/post-plugin-add"
  mkdir -p "${TEST_TEMP_DIR}/mock-bin"

  cat > "${TEST_TEMP_DIR}/mock-bin/git" <<'EOF'
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
  export PATH="${TEST_TEMP_DIR}/mock-bin:$PATH"
}

teardown() {
  rm -rf "${TEST_TEMP_DIR}"
}

@test "php-build submodule points at the revision verified by CI" {
  run "${REAL_GIT}" -C "${BATS_TEST_DIRNAME}/.." ls-files --stage vendor/php-build

  [ "$status" -eq 0 ]
  [[ "$output" =~ ^160000[[:space:]]2180bc5462729543639c928e5da05c90b56b9f7c[[:space:]]0[[:space:]]vendor/php-build$ ]]
}

@test "initializes the pinned submodule and reports its revision" {
  run "${PLUGIN_DIR}/bin/post-plugin-add"

  [ "$status" -eq 0 ]
  [[ "$output" == *"${PINNED_PHP_BUILD_SHA}"* ]]
  grep -F -- "submodule update --init --recursive vendor/php-build" "${MOCK_GIT_LOG}"
  [[ "$output" != *"Cloning php-build"* ]]
}

@test "failed submodule initialization gives a working repair hint without an unpinned clone" {
  export MOCK_SUBMODULE_FAIL=yes

  run "${PLUGIN_DIR}/bin/post-plugin-add"

  [ "$status" -ne 0 ]
  [[ "$output" == *"git submodule update --init --recursive vendor/php-build"* ]]
  [[ "$output" != *"Cloning php-build"* ]]
}
