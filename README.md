# asdf-php

[PHP](https://www.php.net) plugin for asdf version manager

_Original version of this plugin created by
[@Stratus3D](https://github.com/Stratus3D)_

## Build History

[![Build history](https://buildstats.info/github/chart/asdf-community/asdf-php?branch=master)](https://github.com/asdf-community/asdf-php/actions)

## Prerequirements

Check the [.github/workflows/workflow.yml](.github/workflows/workflow.yml) for
dependencies, paths, and environment variables needed to install the latest PHP
version. To be honest, supporting a major version other than the latest without
any extra work from the user is an endless endeavor that won't ever really work
too well. It's not that we don't support them at all, but it's almost impossible
for us to support them.

## Installation

After installing [asdf](https://asdf-vm.com/guide/getting-started.html), install the plugin by running:

```bash
asdf plugin add php https://github.com/asdf-community/asdf-php.git
```

or update an existing installation:

```bash
asdf plugin update php
```

Then use `asdf-php` to manage php:

```bash
# Show all installable versions
asdf list all php

# Install specific version
asdf install php 8.5.0

# or install latest tagged version with
asdf install php latest

# Set a version globally (on your ~/.tool-versions file)
asdf set --home php latest
```

## Note

Composer is installed globally alongside PHP by default. If your application requires additional php extensions, you may need to install them via `pecl`. For example:

```bash
pecl install redis
pecl install imagick

echo "extension=redis.so
extension=imagick.so" > $(asdf where php)/conf.d/php.ini
```

#### macOS

To install PHP on macOS, you'll need a set of packages [installed via homebrew](https://github.com/asdf-community/asdf-php/blob/248e9c6e2a7824510788f05e8cee848a62200b65/.github/workflows/workflow.yml#L52).

There's also a set of optional packages which enable additional extensions to be enabled:

```
brew install gmp libsodium imagemagick
```

Note that the supported extension are not exhaustive, so you may need edit the `bin/install` script to support additional extension. Feel free to submit a PR for any missing extensions.

#### Linux

To install PHP on Linux, you'll need to install build dependencies with development headers:

* autoconf
* re2c
* libxml2
* sqlite
* libcurl
* gd
* oniguruma
* libpq
* readline
* libzip

##### Fedora

Run this command to install required packages:

```sh
sudo dnf install autoconf re2c libxml2 libxml2-devel sqlite sqlite-devel libcurl libcurl-devel gd gd-devel oniguruma oniguruma-devel libpq libpq-devel readline readline-devel libzip libzip-devel
```

##### Debian

Run this command to install required packages:

```sh
sudo apt install autoconf pkg-config gcc bison re2c libxml2-dev libssl-dev sqlite3 libsqlite3-dev zlib1g-dev libcurl4-openssl-dev libgd-dev build-essential libonig-dev libpq-dev libreadline-dev libzip-dev
```

#### PHP-PEAR

If PHP PEAR is down you can install PHP without PEAR. Specify `PHP_WITHOUT_PEAR` variable with any value
(except no), eg:

```bash
PHP_WITHOUT_PEAR=yes asdf install php <version>
```

## Usage

Check [asdf](https://github.com/asdf-vm/asdf) readme for instructions on how to
install & manage versions.

## Global Composer Dependencies

Composer is installed globally by default. To use it, you'll need to reshim:

```shell
composer global require friendsofphp/php-cs-fixer
asdf reshim
php-cs-fixer --version
```

## License

Licensed under the
[Apache License, Version 2.0](https://www.apache.org/licenses/LICENSE-2.0).
