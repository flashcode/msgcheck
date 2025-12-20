<!--
SPDX-FileCopyrightText: 2013-2025 Sébastien Helleu <flashcode@flashtux.org>

SPDX-License-Identifier: GPL-3.0-or-later
-->

# Msgcheck

[![PyPI](https://img.shields.io/pypi/v/msgcheck.svg)](https://pypi.org/project/msgcheck/)
[![Build Status](https://github.com/flashcode/msgcheck/workflows/CI/badge.svg)](https://github.com/flashcode/msgcheck/actions?query=workflow%3A%22CI%22)
[![Build Status](https://github.com/flashcode/msgcheck/workflows/CodeQL/badge.svg)](https://github.com/flashcode/msgcheck/actions?query=workflow%3A%22CodeQL%22)
[![REUSE status](https://api.reuse.software/badge/github.com/flashcode/msgcheck)](https://api.reuse.software/info/github.com/flashcode/msgcheck)

Msgcheck performs various checks on gettext files (with extension `.po`):

- compilation (with command `msgfmt -c`)
- for each translation:
  - number of lines in translated strings
  - whitespace at beginning/end of strings
  - trailing whitespace at end of lines inside strings
  - punctuation at end of strings
  - spelling (messages and translations).

The script requires:

- Python ≥ 3.9
- gettext (for the command `msgfmt`, used to compile PO files)
- the python module `pyenchant` for spell checking (option `-s`).

## Install

Install a released version from the Python package index with pip:

```
$ pip install msgcheck
```

Or you can run via source distribution:

```
$ uv run msgcheck
```

## Usage

Syntax:

```
$ msgcheck [options] file.po [file.po...]
```

Options:

- `-h`, `--help`: display help message and exit
- `-c`, `--no-compile`: do not check compilation of file (with `msgfmt -c`)
- `-f`, `--fuzzy`: check fuzzy strings
- `-n`, `--check-noqa`: check "noqa"-commented lines (they are skipped by default)
- `-l`, `--no-lines`: do not check number of lines
- `-p`, `--no-punct`: do not check punctuation at end of strings
- `-s id|str`, `--spelling id|str`: check spelling (`id` = source messages, `str` = translations)
- `-d <dicts>`, `--dicts <dicts>`: comma-separated list of extra dictionaries to use (in addition to file language)
- `-P <file>`, `--pwl <file>`: file(s) with personal list of words used when checking spelling (this option can be given multiple times)
- `-m`, `--only-misspelled`: display only misspelled words (no error, line number and translation)
- `-w`, `--no-whitespace`: do not check whitespace at beginning/end of strings
- `-W`, `--no-whitespace-eol`: do not check whitespace at end of lines inside strings
- `-e`, `--extract`: display all translations and exit (all checks except compilation are disabled in this mode)
- `-i`, `--ignore-errors`: display but ignore errors (always return 0)
- `-q`, `--quiet`: quiet mode: only display number of errors
- `-v`, `--version`: display version and exit

The environment variable `MSGCHECK_OPTIONS` can be set with some default options.

The script returns exit code **0** if all files checked are OK (0 errors or option
`--extract` given) or it returns **N**: number of files with errors (1 ≤ N ≤ 255).

### pre-commit

To use msgcheck with [pre-commit](https://pre-commit.com/), add the following to your `.pre-commit-config.yaml`:

```yaml
- repo: https://github.com/flashcode/msgcheck
  rev: v4.1.0  # Use the latest tag or a specific commit hash
  hooks:
    - id: msgcheck
      args: []  # add optional arguments like '--fuzzy', see above
```

## Example

```
$ msgcheck fr.po
======================================================================
/path/to/fr.po:242: [punct] end punctuation: ":" in translation, ":" not in string:
---
error
---
erreur:
======================================================================
/path/to/fr.po:262: [lines] number of lines: 1 in string, 2 in translation:
---
Message filters:
---
Filtres de
messages:
======================================================================
/path/to/fr.po:336: [whitespace] spaces at beginning: 0 in string, 1 in translation:
---
current value
---
 valeur courante
======================================================================
/path/to/fr.po: 3 errors (almost good!)
```

## Copyright

<!-- REUSE-IgnoreStart -->
Copyright © 2009-2025 [Sébastien Helleu](https://github.com/flashcode)

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
<!-- REUSE-IgnoreEnd -->
