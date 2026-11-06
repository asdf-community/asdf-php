#!/usr/bin/env bats
# shellcheck disable=SC2292 # Bats assertions are not Bash test syntax.
bats_require_minimum_version 1.7.0

setup() {
  mkdir -p "${BATS_TEST_TMPDIR}/bin"
  cat >"${BATS_TEST_TMPDIR}/bin/git" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' \
  'deadbeef refs/tags/php-8.5.0' \
  'deadbeef refs/tags/php-8.5.0RC1' \
  'deadbeef refs/tags/php-8.5.0beta1' \
  'deadbeef refs/tags/php-8.5.0alpha1' \
  'deadbeef refs/tags/php-8.5.0pl1'
EOF
  chmod +x "${BATS_TEST_TMPDIR}/bin/git"
  export PATH="${BATS_TEST_TMPDIR}/bin:${PATH}"
}

@test "orders PHP pre-releases before the final release and patch level" {
  run -0 "${BATS_TEST_DIRNAME}/../bin/list-all"

  [ "${output}" = "8.5.0alpha1 8.5.0beta1 8.5.0RC1 8.5.0 8.5.0pl1" ]
}
