# Local testing

Run these commands from the plugin checkout. `make check` checks the Python and
Bats tests, ShellCheck, formatting, and the install entrypoint's size.

To test an asdf install without replacing your installed PHP versions, use a
temporary ASDF data directory:

```bash
test_dir="$(mktemp -d)"
ASDF_DATA_DIR="${test_dir}" asdf plugin add php "$(pwd)"
ASDF_DATA_DIR="${test_dir}" asdf install php 8.3.29
"${test_dir}/installs/php/8.3.29/bin/php" -v
"${test_dir}/installs/php/8.3.29/bin/composer" --version
rm -rf -- "${test_dir:?}"
```

`asdf plugin add php "$(pwd)"` clones committed files only. Commit changes
before running this recipe. For an existing local plugin, use
`asdf plugin update php` to fetch new commits; `asdf plugin remove php` also
deletes every PHP version installed by that plugin.

For more build output, run `VERBOSE=y asdf install php 8.3.29`. php-build
writes logs under `${TMPDIR:-/tmp}` on macOS and Linux.
