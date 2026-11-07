# asdf-php

An [asdf](https://asdf-vm.com/) plugin that builds PHP with a pinned
[php-build](https://github.com/php-build/php-build) submodule.

Originally created by [@Stratus3D](https://github.com/Stratus3D).

## Requirements

The installer requires Python 3.9 or newer. Install PHP build dependencies
for your system:

### Ubuntu and Debian

```bash
sudo apt-get install -y autoconf bison build-essential curl git python3 \
  pkg-config re2c ca-certificates libbz2-dev libcurl4-openssl-dev libicu-dev \
  libjpeg-dev libpng-dev libonig-dev libreadline-dev libsqlite3-dev libssl-dev \
  libxml2-dev libzip-dev zlib1g-dev libxslt1-dev libtidy-dev
```

### Arch Linux

```bash
sudo pacman -Syu --needed autoconf bison gcc make re2c pkgconf curl git python \
  ca-certificates libxml2 sqlite oniguruma libzip libjpeg-turbo libpng icu \
  openssl readline zlib bzip2 libxslt tidy
```

### Fedora 44

```bash
sudo dnf install autoconf bison gcc gcc-c++ make re2c curl git python3 \
  pkgconf-pkg-config ca-certificates libxml2-devel sqlite-devel oniguruma-devel \
  libcurl-devel libzip-devel libjpeg-turbo-devel libpng-devel \
  libicu-devel openssl-devel readline-devel zlib-devel bzip2-devel libxslt-devel \
  libtidy-devel
```

`GMP` and `sodium` support is enabled when their development libraries are present.
These extensions are optional. On Ubuntu or Debian install `libgmp-dev` and
`libsodium-dev`; on Arch install `gmp` and `libsodium`; on Fedora install `gmp-devel`
and `libsodium-devel`; on macOS install `gmp` and `libsodium` with Homebrew.
PostgreSQL support is optional too. Install `libpq-dev` on Ubuntu or Debian,
`postgresql-libs` on Arch, `libpq-devel` on Fedora, or `libpq` with Homebrew, then
pass `--with-pgsql` through `PHP_CONFIGURE_OPTIONS`. `GD` uses PHP's bundled library,
so an OS `gd` development package is unnecessary. For `FreeType` font support in `GD`,
install `libfreetype6-dev` on Ubuntu or Debian, `freetype2` on Arch, `freetype-devel`
on Fedora, or `freetype` with Homebrew. `php-build` enables tidy by default on Linux, so these package lists include it.

### macOS

```bash
brew install autoconf bison bzip2 icu4c libedit libiconv libjpeg libpng \
  libxml2 libxslt libzip openssl@3 pkg-config re2c zlib python3
```

For the optional tidy extension, run `brew install tidy-html5`.

## Install and use

```bash
asdf plugin add php https://github.com/asdf-community/asdf-php.git
asdf list all php
asdf install php 8.3.29
asdf set php 8.3.29
php -v
composer --version
```

Use `asdf install php latest` for the latest stable release known to php-build.
Use `asdf plugin update php` to update an existing plugin installation. Adding the
plugin initialises its pinned php-build submodule.

## Build behaviour

- php-build downloads and compiles PHP. Its Composer plugin installs Composer
  alongside each PHP version.
- GMP and sodium are enabled when `pkg-config` finds their libraries. Add
  `--without-gmp` or `--without-sodium` to `PHP_CONFIGURE_OPTIONS` to opt out.
- On macOS, the plugin enables tidy when `tidy-html5` is installed and disables
  it otherwise. The plugin prefers installed `openssl@3` and finds an installed versioned
  `icu4c` keg.
- The plugin sets C++17 for PHP 8.1.33+, 8.2.19+, 8.3.7+, 8.4+, and newer
  releases. Older PHP versions receive compatibility patches where needed.

## Build options

```bash
# Pass additional configure options after the plugin's defaults.
PHP_CONFIGURE_OPTIONS="--without-gmp --without-sodium" asdf install php 8.3.29

# Install OpenSSL 1.1 automatically for legacy PHP when no terminal is available.
ASDF_PHP_OPENSSL_AUTO=yes asdf install php 7.4.33

# Use more build jobs.
ASDF_CONCURRENCY=8 asdf install php 8.3.29
```

PHP 7.4, PHP 8.0 before 8.0.20, and PHP 8.1 before 8.1.6 need OpenSSL 1.1
when the system provides OpenSSL 3. On an interactive terminal, the plugin asks
before installing it. Set `ASDF_PHP_OPENSSL_AUTO=yes` for unattended builds.

## Troubleshooting

- On macOS, install `openssl@3` if a build selects an incompatible OpenSSL.
  Install `tidy-html5` if you need tidy, or use
  `PHP_CONFIGURE_OPTIONS="--without-tidy"` to disable it.
- If php-build is missing from a source checkout, run
  `git submodule update --init --recursive vendor/php-build` there.
- php-build writes logs under `${TMPDIR:-/tmp}`. After a build starts, watch them
  with `tail -f "${TMPDIR:-/tmp}"/php-build.*.log`. Configure errors name the
  missing library or header.

See [local testing](docs/local-testing-manually.md) for a disposable install
recipe.

## Licence

[Apache License 2.0](LICENSE).
