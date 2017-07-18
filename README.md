# asdf-php

[![Build Status](https://travis-ci.org/odarriba/asdf-php.svg?branch=master)](https://travis-ci.org/odarriba/asdf-php)

PHP plugin for [asdf version manager](https://github.com/HashNuke/asdf).

*Original version of this plugin created by [@Stratus3D](https://github.com/Stratus3D)*

## Why using this plug-in?

[Original plug-in](https://github.com/Stratus3D/asdf-php) appears to be unmaintained and it doesn't work anymore (at least on OSX), so I fixed it to provide compatibility and improve it's documentation.

## Install

```
asdf plugin-add php https://github.com/odarriba/asdf-php.git
```

### Linux

You may need this libraries and packages to be able to compile PHP compiler versions:

```
sudo apt-get install curl build-essential autoconf libjpeg-dev libpng12-dev openssl libssl-dev libcurl4-openssl-dev pkg-config libsslcommon2-dev libreadline-dev libedit-dev zlib1g-dev libicu-dev libxml2-dev gettext bison libmysqlclient-dev libpq-dev
```

### macOS

In order to compile PHP on macOS machines, you must install some brew packages first:

```
brew install freetype bison@2.7 gettext icu4c jpeg libpng openssl readline homebrew/dupes/zlib
```

and, in order to compile 5.x versions of PHP, you **must** link `bison27` package:

```
brew link --force bison@2.7
```

## Development

To modify this plugin into your `asdf` installation and see changes live, just create a symlink:

```
ln -s . ~/.asdf/plugins/php
```

## Use

Check the [asdf](https://github.com/HashNuke/asdf) readme for instructions on how to install & manage versions of PHP.

## Contributing

Feel free to create an issue or pull request if you find a bug.

## Issues

### No available versions shown

This could be due to GitHub API quota limits. To solve it, you just need to specify `GITHUB_API_USER` and `GITHUB_API_KEY` with your username and a [Personal Access Token](https://github.com/settings/tokens), so the `list-all` command can use it to fetch available versions.

## License
MIT License
