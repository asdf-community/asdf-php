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

```bash
asdf plugin-add php https://github.com/asdf-community/asdf-php.git
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

To install PHP on macOS, you'll need a set of packages [installed via homebrew](https://github.com/asdf-community/asdf-php/blob/248e9c6e2a7824510788f05e8cee848a62200b65/.github/workflows/workflow.yml#L52):

```
brew install autoconf automake bison freetype gd gettext icu4c krb5 libedit libiconv libjpeg libpng libxml2 libzip pkg-config re2c zlib
```

There's also a set of optional packages which enable additional extensions to be enabled:

```
brew install gmp libsodium imagemagick
```

Note that the supported extension are not exhaustive, so you may need edit the `bin/install` script to support additional extension. Feel free to submit a PR for any missing extensions.

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
