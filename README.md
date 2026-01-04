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

### Linux - Ubuntu/Debian example
```bash
sudo apt-get install -y autoconf bison build-essential curl gettext git \
  libgd-dev libcurl4-openssl-dev libedit-dev libicu-dev libjpeg-dev \
  libmysqlclient-dev libonig-dev libpng-dev libpq-dev libreadline-dev \
  libsqlite3-dev libssl-dev libxml2-dev libzip-dev libtidy-dev openssl \
  pkg-config re2c zlib1g-dev ca-certificates wget libtool automake \
  gcc g++ libxslt1-dev m4 libtool-bin
```

### macOS
```bash
brew install autoconf automake bison freetype gd gettext icu4c krb5 \
  libedit libiconv libjpeg libpng libxml2 libzip openssl@1.1 openssl@3 \
  pkg-config re2c zlib bzip2
```

**Optional extensions:**
```bash
brew install gmp libsodium imagemagick tidy-html5
```

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
./lib/install-openssl11.sh --auto
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

### Build Configuration
```bash
# Disable PEAR installation
export PHP_WITHOUT_PEAR=yes

# Disable Xdebug during build
export PHP_BUILD_XDEBUG_ENABLE=off

# Custom compiler flags
export CFLAGS="-Wno-error -O2"
export CXXFLAGS="-Wno-error -O2"
```

## Extensions and Composer

**Composer** is installed globally alongside PHP by default.

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
tail -f /tmp/php-build.*.log

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
```bash
# If configure can't find libraries:
export LDFLAGS="-L$(brew --prefix)/lib"
export CPPFLAGS="-I$(brew --prefix)/include"
export PKG_CONFIG_PATH="$(brew --prefix icu4c)/lib/pkgconfig:$PKG_CONFIG_PATH"
```

### Manual OpenSSL 1.1 Installation
```bash
# Install OpenSSL 1.1 manually if automatic installation fails
./lib/install-openssl11.sh --help
OPENSSL_SHA256=cf3098950... ./lib/install-openssl11.sh --auto
```

For more examples, see [docs/local-testing-manually.md](docs/local-testing-manually.md).

## License

Licensed under the
[Apache License, Version 2.0](https://www.apache.org/licenses/LICENSE-2.0).
