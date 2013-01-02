## Description

`msgcheck.py` is a Python script used to perform some checks on gettext files
(with extension ".po"):

* check compilation (with command `msgfmt -c`)
* for each translation which is not fuzzy/empty:
  * check number of lines in translated string
  * check spaces at beginning/end of string

The script can run with either Python 2.x or 3.x.

## Usage

Syntax:

    $ python msgcheck.py file.po


## Example

    $ python msgcheck.py fr.po
    Checking compilation of fr.po...
    Checking lines in fr.po...
    ============================================================
    ERROR: number of lines: 1 in string, 2 in translation:

    %s default keys (context: "%s"):


    ============================================================
    ERROR: spaces at end: 0 in string, 1 in translation:

    current value
