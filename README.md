<div align="center">
<h1>asdf-php</h1>
<span><a href="https://www.php.net">PHP</a> plugin for asdf version manager</span>
</div>
<hr />

[![GitHub Workflow Status](https://img.shields.io/github/workflow/status/asdf-community/asdf-php/Main%20workflow?style=flat-square)](https://github.com/asdf-community/asdf-php/actions)<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-1-orange.svg?style=flat-square)](#contributors-)<!-- ALL-CONTRIBUTORS-BADGE:END -->
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](http://makeapullrequest.com)
[![License](https://img.shields.io/github/license/asdf-community/asdf-php?style=flat-square&color=brightgreen)](https://github.com/asdf-community/asdf-php/blob/master/LICENSE)

_Original version of this plugin created by
[@Stratus3D](https://github.com/Stratus3D)_

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

#### Note: PHP-PEAR

PHP PEAR is down without ETA for when the server will be back. To install PHP
without PEAR you can specify a `PHP_WITHOUT_PEAR` variable with any value
(except no), eg:

```bash
PHP_WITHOUT_PEAR=yes asdf install php <version>
```

## Usage

Check [asdf](https://github.com/asdf-vm/asdf) readme for instructions on how to
install & manage versions.

## Contributors ✨

Thanks goes to these wonderful people
([emoji key](https://allcontributors.org/docs/en/emoji-key)):

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tr>
    <td align="center"><a href="https://stratus3d.com/"><img src="https://avatars1.githubusercontent.com/u/1520926?v=4" width="100px;" alt=""/><br /><sub><b>Trevor Brown</b></sub></a><br /><a href="https://github.com/asdf-community/asdf-php/commits?author=Stratus3D" title="Code">💻</a></td>
  </tr>
</table>

<!-- markdownlint-enable -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the
[all-contributors](https://github.com/all-contributors/all-contributors)
specification. Contributions of any kind welcome!

## License

Licensed under the
[Apache License, Version 2.0](https://www.apache.org/licenses/LICENSE-2.0).
