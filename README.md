<div align="center">
<h1>asdf-php</h1>
<span><a href="https://www.php.net">PHP</a> plugin for asdf version manager</span>
</div>
<hr />

[![GitHub Workflow Status](https://img.shields.io/github/workflow/status/asdf-community/asdf-php/Main%20workflow?style=flat-square)](https://github.com/asdf-community/asdf-php/actions)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](http://makeapullrequest.com)
[![License](https://img.shields.io/github/license/asdf-community/asdf-php?style=flat-square&color=brightgreen)](https://github.com/asdf-community/asdf-php/blob/master/LICENSE)

_Original version of this plugin created by
[@Stratus3D](https://github.com/Stratus3D)_

## Installation

```bash
asdf plugin-add php https://github.com/asdf-community/asdf-php.git
```

**Please, remember installing the commonly required libraries that can be found
on the `asdf` README. They are necessary to build PHP versions too!**

### Linux

You may need this libraries and packages to be able to compile PHP compiler
versions:

```bash
sudo apt-get install curl build-essential autoconf libjpeg-dev libpng12-dev openssl libssl-dev libcurl4-openssl-dev pkg-config libsslcommon2-dev libreadline-dev libedit-dev zlib1g-dev libicu-dev libxml2-dev gettext bison libmysqlclient-dev libpq-dev libsqlite3-dev libonig-dev
```

#### Ubuntu 18.04

```bash
sudo apt install curl build-essential libjpeg-dev libpng-dev openssl libcurl4-openssl-dev pkg-config libedit-dev zlib1g-dev libicu-dev libxml2-dev gettext bison libmysqlclient-dev libpq-dev libsqlite3-dev libonig-dev
```

### macOS

To compile PHP on macOS machines, you must install some brew packages first:

```bash
brew install freetype bison bison27 gettext icu4c jpeg libiconv libpng openssl readline zlib
```

Use environment variables to instruct `autoconf` on where to find the libraries
you installed using homebrew. Note that:

- for PHP 5.6, you must use `brew --prefix bison@2.7` in your PATH
- for PHP 7.x, you must use `brew --prefix bison` in your PATH

So replace if necessary:

```bash
PATH="$(brew --prefix bison)/bin:$(brew --prefix icu4c)/bin:$(brew --prefix icu4c)/sbin:$PATH" PHP_CONFIGURE_OPTIONS="--with-iconv=$(brew --prefix libiconv) --with-openssl=$(brew --prefix openssl)" asdf install php <version>
```

**Important note**: There seems to be a bug with PHP `configure` file on recent
versions (> 7.1.4) when using macOS environments. As can be seen in
[this PR](https://github.com/phpbrew/phpbrew/issues/876#issuecomment-301553990),
it's needed to disable `gettext` at build time to work, and later on, impact the
module manually.

To disable it, just execute this **before** run the `asdf install` command:

```bash
export PHP_CONFIGURE_OPTIONS='--disable-gettext'
```

### Note: PHP-PEAR

PHP Pear is down without ETA for when the server will be back. To install PHP
without Pear you can specify a `PHP_WITHOUT_PEAR` variable with any value
(except no), eg:

```bash
PHP_WITHOUT_PEAR=yes asdf install php <version>
```

## Usage

Check [asdf](https://github.com/asdf-vm/asdf) readme for instructions on how to
install & manage versions.

## License

Licensed under the
[Apache License, Version 2.0](https://www.apache.org/licenses/LICENSE-2.0).
