# local testing

Below are the steps to install different versions of PHP using asdf in local environment.

> **Warning:** `asdf plugin remove php` also deletes every PHP version you have installed. `asdf plugin add php <path>` clones committed files only, so commit changes before adding or updating the local plugin. For an existing local plugin, run `asdf plugin update php` to pick up those commits without removing installed PHP versions.

Add the local plugin once with `asdf plugin add php "$(pwd)"`. In the examples below, `asdf plugin update php` refreshes that plugin from its local Git origin.

## install 8.5.11

```bash
asdf uninstall php 8.5.11
asdf plugin update php
ASDF_CONCURRENCY=8 asdf install php 8.5.11
```

## install 8.5.1

```bash
asdf uninstall php 8.5.1
asdf plugin update php

# normal installation
asdf install php 8.5.1

# verbose installation
VERBOSE=y ASDF_CONCURRENCY=4 asdf install php 8.5.1

# install with custom flags
export CFLAGS="-Wno-error -Wno-deprecated-declarations -Wno-implicit-function-declaration -O2"
export CXXFLAGS="-Wno-error -Wno-deprecated-declarations -O2"
export LDFLAGS="-Wl,--no-as-needed"
```

# install 8.3.29

to watch installation progress

```bash
tail -f "${TMPDIR:-/tmp}"/php-build.8.3.29.*.log
```

```bash
asdf uninstall php 8.3.29
asdf plugin update php
asdf install php 8.3.29
➜  ~ asdf set php 8.3.29
# the return should be like
# ➜  ~ php -v
#     PHP 8.3.29 (cli) (built: Dec 25 2025 20:59:03) (NTS)
#     Copyright (c) The PHP Group
#     Zend Engine v4.3.29, Copyright (c) Zend Technologies
#         with Zend OPcache v8.3.29, Copyright (c), by Zend Technologies

# installation with custom flags
export CFLAGS="-Wno-error=dangling-pointer -Wno-error -O2"
export CXXFLAGS="-Wno-error=dangling-pointer -Wno-error -O2"
VERBOSE=y ASDF_CONCURRENCY=4 asdf install php 8.3.29

# monitor installation progress
tail -f "${TMPDIR:-/tmp}"/php-build.8.3.29.*.log

# set as default
asdf set php 8.3.29

# verify installation
php -v
```

## install 8.0.0

```bash
asdf uninstall php 8.0.0
asdf plugin update php
ASDF_CONCURRENCY=8 asdf install php 8.0.0

# monitor installation progress
tail -f "${TMPDIR:-/tmp}"/php-build.8.0.0.*.log

# set as default
asdf set php 8.0.0

# verify installation
php -v
```

## install 7.4.14

```bash
asdf uninstall php 7.4.14
asdf plugin update php
ASDF_CONCURRENCY=8 asdf install php 7.4.14

# monitor installation progress
tail -f "${TMPDIR:-/tmp}"/php-build.7.4.14.*.log

# set as default
asdf set php 7.4.14

# verify installation
php -v
```
