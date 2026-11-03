# asdf-php

[PHP](https://www.php.net) plugin for asdf version manager

_Original version of this plugin created by
[@Stratus3D](https://github.com/Stratus3D)_

## Build History

[Build history](https://github.com/asdf-community/asdf-php/actions)

## Architecture

This plugin uses [php-build](https://github.com/php-build/php-build) as the underlying build system and provides:

- **Legacy PHP Support**: Automatic OpenSSL 1.1 installation for PHP 7.4 and 8.0.x versions
- **Modern Compatibility**: Built-in patches for libxml2 2.12+ and ICU 74+ compatibility
- **Cross-Platform**: Works on Linux, macOS with proper dependency management

## Dependencies

The installer requires Python 3.9 or newer, in addition to the PHP build dependencies below.

### Linux - Ubuntu/Debian example
```bash
sudo apt-get install -y autoconf bison build-essential curl gettext git python3 libbz2-dev \
  libgd-dev libcurl4-openssl-dev libedit-dev libicu-dev libjpeg-dev \
  libgmp-dev libmysqlclient-dev libonig-dev libpng-dev libpq-dev libreadline-dev \
  libsodium-dev libsqlite3-dev libssl-dev libxml2-dev libzip-dev libtidy-dev openssl \
  pkg-config re2c zlib1g-dev ca-certificates wget libtool automake \
  gcc-9 g++-9 libxslt1.1 libxslt1-dev autotools-dev m4 libtool-bin
```

### macOS
```bash
brew install autoconf automake bison freetype gd gettext icu4c krb5 python3 \
  libedit libiconv libjpeg libpng libxml2 libzip openssl@3 \
  pkg-config re2c zlib bzip2
```

**Optional extensions:**
```bash
brew install gmp libsodium imagemagick tidy-html5
```

`gmp` and `libsodium` are enabled automatically when pkg-config finds their libraries, on Linux and macOS. To skip one, add `--without-gmp` or `--without-sodium` to `PHP_CONFIGURE_OPTIONS`.

`tidy` is optional on macOS. The plugin enables it when `tidy-html5` is installed and adds `--without-tidy` when it is absent. Install `tidy-html5` to build the extension, or set `PHP_CONFIGURE_OPTIONS="--without-tidy"` to disable it explicitly.

## Installation

After installing [asdf](https://asdf-vm.com/guide/getting-started.html), install the plugin by running:

```bash
asdf plugin add php https://github.com/asdf-community/asdf-php.git
```

When you add the plugin, asdf runs `bin/post-plugin-add`, which initializes the pinned php-build submodule at `vendor/php-build` and prints its revision. The submodule is pinned to `48f66c3c15eaead0ef362b5349dc85cc24195da3`.

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

# or install the latest stable release that php-build has a definition for
asdf install php latest

# Set a version globally (in ~/.tool-versions)
asdf set php latest

# Or set locally for a project (in ./.tool-versions)
asdf local php 8.3.29
```

## Legacy PHP Support (7.4, 8.0.x)

This plugin automatically handles legacy PHP versions that require OpenSSL 1.1:

```bash
# Automatic OpenSSL 1.1 installation (recommended)
ASDF_PHP_OPENSSL_AUTO=yes asdf install php 7.4.33
ASDF_PHP_OPENSSL_AUTO=yes asdf install php 8.0.30

# Manual OpenSSL 1.1 installation
python3 lib/install-openssl11.py --auto
asdf install php 7.4.33
```

The plugin includes compatibility patches for:
- **libxml2 2.12+** compatibility for PHP 7.4 and 8.0.x
- **ICU 74+** compatibility for PHP 7.4 and 8.0.x

## Environment Variables

### OpenSSL Configuration
```bash
# Enable automatic OpenSSL 1.1 installation for legacy PHP
export ASDF_PHP_OPENSSL_AUTO=yes

# Manual OpenSSL paths (if needed)
export PKG_CONFIG_PATH="/path/to/openssl-1.1/lib/pkgconfig:$PKG_CONFIG_PATH"
export PHP_BUILD_CONFIGURE_OPTS="--with-openssl=/path/to/openssl-1.1"
```

On macOS, when openssl@3 is installed, the plugin builds against it automatically. The openssl@4 headers do not compile PHP 8.3.x, so the plugin puts openssl@3 first in `PKG_CONFIG_PATH` and `LDFLAGS`, and adds `--with-openssl`. If you set `--with-openssl` or a `PKG_CONFIG_PATH` that starts with an OpenSSL directory yourself, the plugin leaves your settings alone.

### Build Configuration
```bash
# Disable PEAR installation
export PHP_WITHOUT_PEAR=yes

# Leave Xdebug disabled in xdebug.ini (the extension is still built)
export PHP_BUILD_XDEBUG_ENABLE=off

# Custom compiler flags
export CFLAGS="-Wno-error -O2"
export CXXFLAGS="-Wno-error -O2"

# Extra configure flags, added after the plugin's defaults (a later flag wins)
export PHP_CONFIGURE_OPTIONS="--without-tidy"
```

PHP 7.4 on macOS is built without Xdebug, because Xdebug 3.1.6 does not compile with the macOS toolchain.

For PHP 8.1.33+, 8.2.19+, 8.3.7+ and 8.4+, the plugin sets `-std=c++17` itself, replacing any `-std=` in `CXXFLAGS`, because ICU 74+ needs C++17.

## Extensions and Composer

**Composer** is installed with each PHP version by default. Composer runs through `php`, so `composer` needs a PHP version selected in asdf, for example `asdf local php 8.3.29` in your project.

**PECL Extensions:**
```bash
pecl install redis imagick

# Add to PHP configuration
echo "extension=redis.so
extension=imagick.so" >> $(asdf where php)/conf.d/extensions.ini
```

**Global Composer packages:**
```bash
composer global require friendsofphp/php-cs-fixer
asdf reshim php
php-cs-fixer --version
```

## Usage

### Version Management
```bash
# List installed versions
asdf list php

# Show current version
asdf current php

# Switch versions
asdf set php 8.3.29        # Set globally
asdf local php 7.4.33      # Set for current project

# Uninstall a version
asdf uninstall php 8.0.30
```

### Monitoring Installation
```bash
# Watch build progress
tail -f "${TMPDIR:-/tmp}"/php-build.*.log

# Verbose installation
VERBOSE=y asdf install php 8.3.29
```

## Troubleshooting

### Legacy PHP Build Issues
```bash
# For PHP 7.4/8.0.x compilation errors:
export ASDF_PHP_OPENSSL_AUTO=yes
export CFLAGS="-Wno-error -Wno-deprecated-declarations -O2"
export CXXFLAGS="-Wno-error -Wno-deprecated-declarations -O2"
asdf install php 7.4.33
```

### macOS Issues
- **`ERR_NUM_ERRORS` while compiling `ext/openssl`:** install `openssl@3` with `brew install openssl@3`. The plugin builds against it automatically when it is installed.
- **`Cannot find libtidy`:** install `tidy-html5` with `brew install tidy-html5`, or build without tidy with `PHP_CONFIGURE_OPTIONS="--without-tidy"`.

```bash
# If configure can't find libraries:
export LDFLAGS="-L$(brew --prefix)/lib"
export CPPFLAGS="-I$(brew --prefix)/include"
export PKG_CONFIG_PATH="$(brew --prefix icu4c)/lib/pkgconfig:$PKG_CONFIG_PATH"
```

### Manual OpenSSL 1.1 Installation
```bash
# Install OpenSSL 1.1 manually if automatic installation fails
python3 lib/install-openssl11.py --help
OPENSSL_SHA256=cf3098950... python3 lib/install-openssl11.py --auto
```

For more examples, see [docs/local-testing-manually.md](docs/local-testing-manually.md).

## License

Licensed under the
[Apache License, Version 2.0](https://www.apache.org/licenses/LICENSE-2.0).
