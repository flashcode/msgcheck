## Description

`msgcheck` performs various checks on gettext files (with extension ".po"):

* compilation (with command `msgfmt -c`)
* for each translation:
  * number of lines in translated strings
  * whitespace at beginning/end of strings
  * trailing whitespace at end of lines inside strings
  * punctuation at end of strings
  * spelling (messages and translations)

The script requires Python >= 2.7.

Module `pyenchant` is required if spelling is checked (option `-s`).

[![Build Status](https://travis-ci.org/flashcode/msgcheck.svg?branch=master)](https://travis-ci.org/flashcode/msgcheck)

## Install

Install a released version from the Python package index with pip:

    $ pip install msgcheck

Install via source distribution:

    $ python setup.py install

## Usage

Syntax:

    $ msgcheck [options] file.po [file.po...]

Options:

* `-h`, `--help`: display help message and exit
* `-c`, `--no-compile`: do not check compilation of file (with `msgfmt -c`)
* `-f`, `--fuzzy`: check fuzzy strings
* `-l`, `--no-lines`: do not check number of lines
* `-p`, `--no-punct`: do not check punctuation at end of strings
* `-s id|str`, `--spelling id|str`: check spelling (`id` = source messages,
  `str` = translations)
* `-d <dicts>`, `--dicts <dicts>`: comma-separated list of extra dictionaries
  to use (in addition to file language)
* `-P <file>`, `--pwl <file>`: file with personal word list used when checking
  spelling
* `-m`, `--only-misspelled`: display only misspelled words (no error, line
  number and translation)
* `-w`, `--no-whitespace`: do not check whitespace at beginning/end of strings
* `-W`, `--no-whitespace-eol`: do not check whitespace at end of lines inside
  strings
* `-e`, `--extract`: display all translations and exit (all checks except
  compilation are disabled in this mode)
* `-q`, `--quiet`: quiet mode: only display number of errors
* `-v`, `--version`: display version and exit

Environment variable `MSGCHECK_OPTIONS` can be set with some default options.

The script returns following exit code:
  0: all files checked are OK (0 errors) (or --extract given)
  n: number of files with errors (n >= 1)

## Example

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

## Copyright

Copyright (C) 2009-2014 Sébastien Helleu <flashcode@flashtux.org>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
