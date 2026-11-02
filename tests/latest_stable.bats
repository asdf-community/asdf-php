#!/usr/bin/env bats
# shellcheck disable=SC2292 # Bats assertions are not Bash test syntax.
bats_require_minimum_version 1.7.0

setup() {
  LATEST_STABLE="${BATS_TEST_DIRNAME}/../bin/latest-stable"
  mkdir -p "${BATS_TEST_TMPDIR}/mock-bin"

  # latest-stable only calls "git ls-remote --tags <php-src url>"; answer with a
  # fixed tag list that includes a release candidate and a peeled tag.
  cat >"${BATS_TEST_TMPDIR}/mock-bin/git" <<'EOF'
#!/usr/bin/env bash
sha=0000000000000000000000000000000000000000
for tag in 8.2.30 8.3.5 8.3.29 8.4.1 8.4.1RC1; do
  printf '%s\trefs/tags/php-%s\n' "${sha}" "${tag}"
done
printf '%s\trefs/tags/php-8.3.29^{}\n' "${sha}"
EOF
  chmod +x "${BATS_TEST_TMPDIR}/mock-bin/git"
  export PATH="${BATS_TEST_TMPDIR}/mock-bin:${PATH}"
}

@test "prints the newest stable release when called without arguments" {
  run -0 "${LATEST_STABLE}"

  [ "${output}" = "8.4.1" ]
}

@test "treats the empty argument asdf passes for plain latest as no filter" {
  run -0 "${LATEST_STABLE}" ""

  [ "${output}" = "8.4.1" ]
}

@test "limits the result to a major.minor line" {
  run -0 "${LATEST_STABLE}" 8.3

  [ "${output}" = "8.3.29" ]
}

@test "rejects a query that is not a major.minor version" {
  run -2 "${LATEST_STABLE}" abc

  [ "${output}" = "latest-stable: expected a major.minor version, got abc" ]
}

@test "exits 1 when no release matches the query" {
  run -1 "${LATEST_STABLE}" 9.9
}
