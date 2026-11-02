#!/usr/bin/env bats
# shellcheck disable=SC2292 # Bats assertions are not Bash test syntax.
bats_require_minimum_version 1.7.0

setup() {
  local plugin="${BATS_TEST_TMPDIR}/plugin" name
  DEFINITIONS="${plugin}/vendor/php-build/share/php-build/definitions"
  mkdir -p "${plugin}/bin" "${DEFINITIONS}" "${BATS_TEST_TMPDIR}/mock-bin"
  cp "${BATS_TEST_DIRNAME}/../bin/latest-stable" "${plugin}/bin/latest-stable"
  LATEST_STABLE="${plugin}/bin/latest-stable"

  # latest-stable reads the definitions that ship with php-build. Besides the
  # stable releases, add a snapshot and pre-releases that sort after all of them.
  for name in 8.2.30 8.3.5 8.3.29 8.4.1 8.5snapshot 8.5.0RC1 8.6.0alpha1; do
    touch "${DEFINITIONS}/${name}"
  done

  # It must not need the network: any call to git fails the run.
  printf '#!/usr/bin/env bash\nexit 99\n' >"${BATS_TEST_TMPDIR}/mock-bin/git"
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

@test "does not offer a release php-build has no definition for" {
  rm "${DEFINITIONS}/8.4.1"

  run -0 "${LATEST_STABLE}"

  [ "${output}" = "8.3.29" ]
}

@test "rejects a query that is not a major.minor version" {
  run -2 "${LATEST_STABLE}" abc

  [ "${output}" = "latest-stable: expected a major.minor version, got abc" ]
}

@test "exits 1 when no release matches the query" {
  run -1 "${LATEST_STABLE}" 9.9
}

@test "exits 1 when php-build has no stable release" {
  rm "${DEFINITIONS}"/*

  run -1 "${LATEST_STABLE}"
}

@test "explains how to fetch php-build when its definitions are missing" {
  rm -r "${DEFINITIONS}"

  run -1 "${LATEST_STABLE}"

  [ "${lines[0]}" = "latest-stable: php-build definitions not found at ${DEFINITIONS}" ]
  [ "${lines[1]}" = "  run: git submodule update --init --recursive" ]
}
