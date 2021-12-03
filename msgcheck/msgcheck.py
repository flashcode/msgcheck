#!/usr/bin/env python3
#
# Copyright (C) 2009-2021 Sébastien Helleu <flashcode@flashtux.org>
#
# This file is part of msgcheck.
#
# Msgcheck is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# Msgcheck is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with msgcheck.  If not, see <https://www.gnu.org/licenses/>.
#

"""
Perform various checks on gettext files:
* compilation (with command `msgfmt -c`)
* for each translation:
  * number of lines in translated strings
  * whitespace at beginning/end of strings
  * trailing whitespace at end of lines inside strings
  * punctuation at end of strings
  * spelling (messages and translations)
"""

from __future__ import print_function

import argparse
import os
import shlex
import sys

from . po import PoCheck


__version__ = '3.2.0-dev'


def msgcheck_version():
    """Return the msgcheck version."""
    return __version__


def msgcheck_parser():
    """Return a command line parser for msgcheck (argparse.ArgumentParser)."""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        fromfile_prefix_chars='@',
        description='Gettext file checker.',
        epilog='''
Environment variable "MSGCHECK_OPTIONS" can be set with default options.
Argument "@file.txt" can be used to read default options in a file.

The script returns:
  0: all files checked are OK (or one of these options given:
     --extract, --only-misspelled or --ignore-errors given)
  n: number of files with errors (1 ≤ n ≤ 255)
''')
    parser.add_argument('-c', '--no-compile', action='store_true',
                        help='do not check compilation of file')
    parser.add_argument('-f', '--fuzzy', action='store_true',
                        help='check fuzzy strings')
    parser.add_argument('-n', '--skip-noqa', action='store_true',
                        help='do not check "noqa"-commented lines')
    parser.add_argument('-l', '--no-lines', action='store_true',
                        help='do not check number of lines')
    parser.add_argument('-p', '--no-punct', action='store_true',
                        help='do not check punctuation at end of strings')
    parser.add_argument('-s', '--spelling', choices=['id', 'str'],
                        help='check spelling')
    parser.add_argument('-d', '--dicts',
                        help='comma-separated list of extra dictionaries '
                        'to use (in addition to file language)')
    parser.add_argument('-P', '--pwl', action='append',
                        help='file(s) with personal list of words used when '
                        'checking spelling (this option can be given multiple '
                        'times)')
    parser.add_argument('-m', '--only-misspelled', action='store_true',
                        help='display only misspelled words (no error, '
                        'line number and translation)')
    parser.add_argument('-w', '--no-whitespace', action='store_true',
                        help='do not check whitespace at beginning/end of '
                        'strings')
    parser.add_argument('-W', '--no-whitespace-eol', action='store_true',
                        help='do not check trailing whitespace at end of '
                        'lines inside strings')
    parser.add_argument('-e', '--extract', action='store_true',
                        help='display all translations and exit '
                        '(all checks except compilation are disabled in '
                        'this mode)')
    parser.add_argument('-i', '--ignore-errors', action='store_true',
                        help='display but ignore errors (always return 0)')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='quiet mode: only display number of errors')
    parser.add_argument('-v', '--version', action='version',
                        version=msgcheck_version())
    parser.add_argument('file', nargs='+',
                        help='gettext file(s) to check (*.po files)')
    return parser


def msgcheck_args(parser):
    """Return msgcheck options."""
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    return parser.parse_args(
        shlex.split(os.getenv('MSGCHECK_OPTIONS') or '') + sys.argv[1:])


def msgcheck_check_files(args):
    """Check files."""
    # create checker and set boolean options
    po_check = PoCheck()
    for option in ('no_compile', 'fuzzy', 'skip_noqa', 'no_lines', 'no_punct',
                   'no_whitespace', 'no_whitespace_eol', 'extract'):
        if args.__dict__[option]:
            po_check.set_check(option.lstrip('no_'),
                               not option.startswith('no_'))

    # check all files
    try:
        po_check.set_spelling_options(args.spelling, args.dicts, args.pwl)
        result = po_check.check_files(args.file)
    except (ImportError, IOError) as exc:
        print('FATAL:', exc, sep=' ')
        sys.exit(1)

    return result


def msgcheck_display_errors(args, result):
    """Display error messages."""
    files_ok, files_with_errors, total_errors = 0, 0, 0
    for _, reports in result:
        if not reports:
            files_ok += 1
            continue
        files_with_errors += 1
        total_errors += len(reports)
        if not args.quiet:
            if args.only_misspelled:
                words = []
                for report in reports:
                    for word in report.get_misspelled_words():
                        words.append(word)
                print('\n'.join(sorted(set(words),
                                       key=lambda s: s.lower())))
            else:
                print('\n'.join([str(report) for report in reports]))
    return files_ok, files_with_errors, total_errors


def msgcheck_display_result(args, result):
    """Display result and return the number of files with errors."""
    # display errors
    files_ok, files_with_errors, total_errors = \
        msgcheck_display_errors(args, result)

    # exit now if we extracted translations or if we displayed only
    # misspelled words
    if args.extract or args.only_misspelled:
        sys.exit(0)

    # display files with number of errors
    if total_errors > 0 and not args.quiet:
        print('=' * 70)
    for filename, reports in result:
        errors = len(reports)
        if errors == 0:
            print(f'{filename}: OK')
        else:
            result = 'almost good!' if errors <= 10 else 'uh oh... try again!'
            print(f'{filename}: {errors} errors ({result})')

    # display total (if many files processed)
    if len(args.file) > 1:
        print('---')
        if files_with_errors == 0:
            print(f'TOTAL: {files_ok} files OK')
        else:
            print(f'TOTAL: {files_ok} files OK, {files_with_errors} files '
                  f'with {total_errors} errors')

    return files_with_errors


def main():  # pylint: disable=too-many-branches
    """Main function."""
    args = msgcheck_args(msgcheck_parser())
    result = msgcheck_check_files(args)
    files_with_errors = msgcheck_display_result(args, result)
    sys.exit(0 if args.ignore_errors else min(files_with_errors, 255))


if __name__ == "__main__":
    main()
