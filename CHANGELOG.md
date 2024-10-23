# Msgcheck ChangeLog

## Version 4.1.0 (2024-10-23)

### Changed

- Use file README.md as package long description

### Fixed

- Fix UnicodeDecodeError in case of invalid UTF-8 in input file

## Version 4.0.0 (2022-01-23)

### Changed

- **Breaking**: drop Python 2 support, Python 3.6 is now required
- **Breaking**: rename option `--skip-noqa` to `--check-noqa` and reverse behavior: without option, strings with `noqa` are now skipped by default

### Added

- Add support for Chinese full-stop
- Add lint with bandit in CI

## Version 3.1 (2020-03-07)

### Changed

- Use pytest for unit tests
- Replace Travis CI by GitHub Actions

### Added

- Add option `-i` (or `--ignore-errors`): always return 0 even if errors are found

### Fixed

- Fix parsing of "noqa" tag in comments ([#11](https://github.com/flashcode/msgcheck/issues/11))

## Version 3.0 (2018-12-14)

### Changed

- Add support of multiple personal word list files (multiple options `-P`/`--pwl`) ([#5](https://github.com/flashcode/msgcheck/issues/5))

## Version 2.9 (2018-01-15)

### Added

- Add option `-n` (or `--skip-noqa`) to not check "noqa"-commented lines ([#2](https://github.com/flashcode/msgcheck/issues/2), [#7](https://github.com/flashcode/msgcheck/issues/7))

### Fixed

- Remove C and Python string formatters for spell checking ([#3](https://github.com/flashcode/msgcheck/issues/3))

## Version 2.8 (2014-12-07)

### Changed

- Display multiple misspelled words on same error line
- Sort and keep unique misspelled words with option `-m`/`--only-misspelled`

### Fixed

- Fix read of fuzzy flag

## Version 2.7 (2014-06-28)

### Changed

- **Breaking**: add argument id/str for `-s`/`--spelling` to check messages or translations

### Added

- Add pylint checks for Travis CI

### Fixed

- Ensure pwl is not None before checking if file exists
- Exit immediately if pwl file does not exist

## Version 2.6 (2014-05-03)

### Added

- Add tests with Travis CI
- Code refactoring, add setup.py and tests

### Fixed

- Fix return code when there are more than 255 files with errors

## Version 2.5 (2014-04-26)

### Changed

- Code cleanup

## Version 2.4 (2014-03-18)

### Added

- Add option `-W` (or `--no-whitespace-eol`) to not check trailing whitespace at end of lines inside strings

## Version 2.3 (2014-01-20)

### Fixed

- Fix error with `--spelling`

## Version 2.2 (2013-11-08)

### Changed

- Add a main function

## Version 2.1 (2013-11-02)

### Changed

- **Breaking**: rename some long names for command line options
- Use codecs module to unescape strings (faster with python 3)
- Add short option synonym `-P` for `--pwl`
- Add short option synonym `-e` for `--extract`
- Major code cleanup: add comments, move checking/error functions from class PoMessage to class PoFile
- Full PEP8 compliance

### Fixed

- Fix problem when latest string in file has a plural form (this last translation was ignored)
- Display full exception in case of problem when reading file

## Version 2.0 (2013-09-23)

### Added

- Display number of files OK when there are multiple files checked and no errors

## Version 1.9 (2013-09-21)

### Added

- Add short option `-m` for `--onlymisspelled`

## Version 1.8 (2013-09-21)

### Added

- Add option `-d` (or `--dicts`) to use extra dictionaries for spell checking

## Version 1.7 (2013-09-21)

### Added

- Add option `--onlymisspelled` to display only misspelled words instead of errors with translations

## Version 1.6 (2013-09-15)

### Added

- Add option `--extract` to extract translations

## Version 1.5 (2013-09-15)

### Added

- Add option `-s` (or `--spelling`) to check spelling and option `--pwl` to use a personal list of words (with module `python-enchant`)

## Version 1.4 (2013-09-14)

### Changed

- **Breaking**: rename arguments: `-n` to `-l`, `-s` to `-w`
- Use argparse module to parse command line arguments, allow long name for arguments
- Display "(fuzzy)" after line number and colon in error messages

### Fixed

- Fix detection of fuzzy strings in gettext files

## Version 1.3 (2013-08-23)

### Changed

- **Breaking**: use absolute path for filenames displayed

## Version 1.2 (2013-07-02)

### Fixed

- Remove some fancy chars in output so that output can be used as compilation output in editors like Emacs

## Version 1.1 (2013-07-01)

### Added

- Read environment variable `MSGCHECK_OPTIONS`

## Version 1.0 (2013-07-01)

### Added

- Add option `-c` (do not check compilation)

## Version 0.9 (2013-07-01)

### Fixed

- Use specific period for Japanese when checking punctuation

## Version 0.8 (2013-06-30)

### Changed

- Use own .po parser (about 200x faster!)

### Added

- Add options `-f` (check fuzzy), `-q` (quiet) and `-v` (display version)

## Version 0.7 (2013-06-29)

### Added

- Add options to disable some checks

## Version 0.6 (2013-06-29)

### Added

- Check punctuation at end of string

## Version 0.5 (2013-01-02)

### Changed

- **Breaking**: rename script to `msgcheck.py`
- Display syntax when script is called without filename
- Replace os.system by subprocess

## Version 0.4 (2012-09-21)

### Added

- Add check of compilation with `msgfmt -c`

## Version 0.3 (2011-04-14)

### Added

- Allow multiple po filenames

## Version 0.2 (2011-04-10)

### Added

- Add check of spaces at beginning/end of strings

## Version 0.1 (2010-03-22)

### Added

- First release
