## Description

`msgcheck.py` is a Python script used to perform some checks on gettext files
(with extension ".po"):

* check compilation (with command `msgfmt -c`)
* for each translation:
  * check number of lines in translated string
  * check spaces at beginning/end of string
  * check punctuation at end of string

The script can run with either Python 2.x or 3.x.

Module `python-enchant` is required if spelling is checked (option `-s`).

## Usage

Syntax:

    $ python msgcheck.py [options] file.po [file.po...]

Options:

* `-h`, `--help`: display help message and exit
* `-c`, `--compile`: do not check compilation of file (with `msgfmt -c`)
* `-f`, `--fuzzy`: check fuzzy strings (default: ignored)
* `-l`, `--lines`: do not check number of lines
* `-p`, `--punct`: do not check punctuation at end of string
* `-s`, `--spelling`: check spelling
* `--pwl <file>`: file with personal word list used when checking spelling
* `-w`, `--whitespace`: do not check whitespace at beginning/end of string
* `-q`, `--quiet`: quiet mode: only display number of errors
* `-v`, `--version`: display version and exit

Environment variable 'MSGCHECK_OPTIONS' can be set with some default options.

## Example

    $ python msgcheck.py fr.po
    ======================================================================
    /path/to/fr.po:242: end punctuation: ":" in translation, ":" not in string:
    ---
    error
    ---
    erreur:
    ======================================================================
    /path/to/fr.po:262: number of lines: 1 in string, 2 in translation:
    ---
    Message filters:
    ---
    Filtres de
    messages:
    ======================================================================
    /path/to/fr.po:336: spaces at beginning: 0 in string, 1 in translation:
    ---
    current value
    ---
     valeur courante
    ======================================================================
    fr.po: 3 errors (almost good!)
