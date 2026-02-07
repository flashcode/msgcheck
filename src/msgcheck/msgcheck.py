#
# SPDX-FileCopyrightText: 2009-2026 Sébastien Helleu <flashcode@flashtux.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later
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

"""Perform various checks on gettext files.

Checks:

- compilation (with command `msgfmt -c`)
- for each translation:
  - number of lines in translated strings
  - whitespace at beginning/end of strings
  - trailing whitespace at end of lines inside strings
  - punctuation at end of strings
  - spelling (messages and translations)
"""

# ruff: noqa: T201

import argparse
import importlib.metadata
import os
import shlex
import sys

from msgcheck.po import PoCheck, PoFileReport

HELP_OUTPUT_FORMATS = [
    "full = complete output",
    "oneline = one line output",
    "extract = display all translations (all checks except compilation are disabled in this mode)",
    "misspelled = display only misspelled words",
]


class CustomHelpFormatter(argparse.RawDescriptionHelpFormatter, argparse.ArgumentDefaultsHelpFormatter):
    """Help formatter with raw description/epilog and default values."""


def msgcheck_parser() -> argparse.ArgumentParser:
    """Return a command line parser for msgcheck."""
    parser = argparse.ArgumentParser(
        formatter_class=CustomHelpFormatter,
        fromfile_prefix_chars="@",
        description="Gettext file checker.",
        epilog="""
Environment variable "MSGCHECK_OPTIONS" can be set with default options.
Argument "@file.txt" can be used to read default options in a file.

The script returns:
  0: all files checked are OK (or one of these options given:
     --output-format={extract|misspelled} or --ignore-errors given)
  n: number of files with errors (1 ≤ n ≤ 255)
""",
    )
    parser.add_argument(
        "-c",
        "--no-compile",
        action="store_true",
        help="do not check compilation of file",
    )
    parser.add_argument(
        "-f",
        "--fuzzy",
        action="store_true",
        help="check fuzzy strings",
    )
    parser.add_argument(
        "-F",
        "--error-on-fuzzy",
        action="store_true",
        help="raise an error if fuzzy strings are found",
    )
    parser.add_argument(
        "-n",
        "--check-noqa",
        action="store_true",
        help='check "noqa"-commented lines (they are skipped by default)',
    )
    parser.add_argument(
        "-l",
        "--no-lines",
        action="store_true",
        help="do not check number of lines",
    )
    parser.add_argument(
        "-p",
        "--no-punct",
        action="store_true",
        help="do not check punctuation at end of strings",
    )
    parser.add_argument(
        "-s",
        "--spelling",
        choices=["id", "str"],
        help="check spelling",
    )
    parser.add_argument(
        "-d",
        "--dicts",
        help="comma-separated list of extra dictionaries to use (in addition to file language)",
    )
    parser.add_argument(
        "-P",
        "--pwl",
        action="append",
        help="file(s) with personal list of words used when "
        "checking spelling (this option can be given multiple "
        "times)",
    )
    parser.add_argument(
        "-m",
        "--only-misspelled",
        action="store_true",
        help="display only misspelled words (alias of --output-format=misspelled)",
    )
    parser.add_argument(
        "-w",
        "--no-whitespace",
        action="store_true",
        help="do not check whitespace at beginning/end of strings",
    )
    parser.add_argument(
        "-W",
        "--no-whitespace-eol",
        action="store_true",
        help="do not check trailing whitespace at end of lines inside strings",
    )
    parser.add_argument(
        "-e",
        "--extract",
        action="store_true",
        help="display all translations and exit (alias of --output-format=extract)",
    )
    parser.add_argument(
        "-i",
        "--ignore-errors",
        action="store_true",
        help="display but ignore errors (always return 0)",
    )
    parser.add_argument(
        "-o",
        "--output-format",
        choices=["full", "oneline", "extract", "misspelled"],
        default="full",
        help=f"output format: {', '.join(HELP_OUTPUT_FORMATS)}",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="quiet mode: only display number of errors",
    )
    version = importlib.metadata.version("msgcheck")
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=version,
    )
    parser.add_argument(
        "files",
        nargs="+",
        help="files or directories with gettext files (*.po)",
    )
    return parser


def msgcheck_args(parser: argparse.ArgumentParser) -> argparse.Namespace:
    """Return msgcheck options."""
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    return parser.parse_args(shlex.split(os.getenv("MSGCHECK_OPTIONS") or "") + sys.argv[1:])


def msgcheck_check_files(args: argparse.Namespace) -> list[PoFileReport]:
    """Check files."""
    # create checker and set boolean options
    po_check = PoCheck()
    for option in (
        "no_compile",
        "fuzzy",
        "check_noqa",
        "no_lines",
        "no_punct",
        "no_whitespace",
        "no_whitespace_eol",
        "error_on_fuzzy",
    ):
        if args.__dict__[option]:
            po_check.set_check(option.lstrip("no_"), not option.startswith("no_"))
    if args.extract:
        args.output_format = "extract"
    elif args.only_misspelled:
        args.output_format = "misspelled"
    if args.output_format == "extract":
        po_check.set_check("extract")

    # check all files
    try:
        po_check.set_spelling_options(args.spelling, args.dicts, args.pwl)
        result = po_check.check_files(args.files)
    except (ImportError, OSError) as exc:
        print("FATAL:", exc, sep=" ")
        sys.exit(1)

    return result


def msgcheck_display_errors(args: argparse.Namespace, result: list[PoFileReport]) -> tuple[int, int, int]:
    """Display error messages."""
    files_ok, files_with_errors, total_errors = 0, 0, 0
    for report in result:
        if not report:
            files_ok += 1
            continue
        files_with_errors += 1
        total_errors += len(report)
        if not args.quiet:
            if args.output_format == "misspelled":
                words = []
                for error in report:
                    words.extend(error.get_misspelled_words())
                if words:
                    print("\n".join(sorted(set(words), key=lambda s: s.lower())))
            else:
                print("\n".join([error.to_string(fmt=args.output_format) for error in report]))
    return files_ok, files_with_errors, total_errors


def msgcheck_display_result(args: argparse.Namespace, result: list[PoFileReport]) -> int:
    """Display result and return the number of files with errors."""
    # display errors
    files_ok, files_with_errors, total_errors = msgcheck_display_errors(args, result)

    # exit now if we extracted translations or if we displayed only misspelled words
    if args.output_format in ("extract", "misspelled"):
        sys.exit(0)

    # display files with number of errors
    if args.output_format == "full":
        if total_errors > 0 and not args.quiet:
            print("=" * 70)
        for report in result:
            errors = len(report)
            if errors == 0:
                print(f"{report.filename}: OK")
            else:
                str_result = "almost good!" if errors <= 10 else "uh oh... try again!"  # noqa: PLR2004
                print(f"{report.filename}: {errors} errors ({str_result})")

    # display total (if many files processed)
    if args.output_format == "full":
        str_errors = f", {files_with_errors} files with {total_errors} errors" if files_with_errors > 0 else ""
        print(f"TOTAL: {files_ok} files OK{str_errors}")

    return files_with_errors


def check() -> None:
    """Check gettext files."""
    args = msgcheck_args(msgcheck_parser())
    result = msgcheck_check_files(args)
    files_with_errors = msgcheck_display_result(args, result)
    sys.exit(0 if args.ignore_errors else min(files_with_errors, 255))
