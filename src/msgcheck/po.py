#
# SPDX-FileCopyrightText: 2009-2025 Sébastien Helleu <flashcode@flashtux.org>
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

"""Classes to read and check PO (gettext) files."""

# ruff: noqa: FBT001,FBT002,T201

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from codecs import escape_decode
from pathlib import Path
from typing import Any

from enchant import Dict, DictNotFoundError, DictWithPWL
from enchant.checker import SpellChecker

from msgcheck.utils import count_lines, replace_formatters


def get_concatenated_files(filenames: list[str]) -> str | None:
    """Return concatenated content of multiple files."""
    if not filenames:
        return None
    content = []
    for filename in filenames:
        with Path(filename).open("rb") as _file:
            content.append(_file.read().decode("utf-8"))
    return "\n".join(content)


class PoReport:
    """A message in report (commonly an error in detected in gettext file)."""

    def __init__(  # noqa: PLR0913
        self,
        message: str | list[str],
        idmsg: str = "",
        filename: str = "-",
        line: int = 0,
        mid: str = "",
        mstr: str = "",
        fuzzy: bool = False,
    ) -> None:
        """Initialize PO report."""
        self.message = message
        self.idmsg = idmsg
        self.filename = filename
        self.line = line
        self.mid = mid
        self.mstr = mstr
        self.fuzzy = fuzzy

    def to_string(self, fmt: str = "full") -> str:  # noqa: PLR0911
        """Return PO report as string."""
        if self.idmsg == "extract":
            if isinstance(self.message, list):
                return ", ".join(self.message) + "\n---"
            return self.message + "\n---"
        if self.idmsg == "compile":
            if fmt == "oneline":
                if isinstance(self.message, list):
                    return self.message[0]
                return self.message.split("\n")[0]
            return f"{'=' * 70}\n{self.message}"
        is_list = isinstance(self.message, list)
        count = f"({len(self.message)})" if is_list else ""
        str_fuzzy = "(fuzzy) " if self.fuzzy else ""
        str_msg = ", ".join(self.message) if is_list else self.message
        if fmt == "oneline":
            return f"{self.filename}:{self.line}: [{self.idmsg}{count}] {str_fuzzy}{str_msg}"
        msg = f"{'=' * 70}\n{self.filename}:{self.line}: [{self.idmsg}{count}] {str_fuzzy}{str_msg}"
        if self.mid:
            msg += "\n---\n" + self.mid
        if self.mstr:
            msg += "\n---\n" + self.mstr
        return msg

    def get_misspelled_words(self) -> list[str]:
        """Return list of misspelled words."""
        return self.message if isinstance(self.message, list) else []


class PoFileReport(list):
    """A file report."""

    def __init__(self, filename: str = "-") -> None:
        """Initialize PO file report."""
        self.filename = filename


class PoMessage:
    """A message from a gettext file.

    It is stored as a list of tuples (string, translation).
    The list usually have one element, except if the plural form is used.

    Example of a single string (french translation):

        msgid "Hello"
        msgstr "Bonjour"

        ==>  [("Hello", "Bonjour")]

    Example with a plural form (french translations):

        #, c-format
        msgid "%d file found"
        msgid_plural "%d files found"
        msgstr[0] "%d fichier trouvé"
        msgstr[1] "%d fichiers trouvés"

        ==>  [("%d files found", "%d fichier trouvé"),
              ("%d files found", "%d fichiers trouvés")]
    """

    def __init__(  # noqa: PLR0913
        self,
        filename: str,
        line: int,
        msg: dict[str, str],
        charset: str,
        fuzzy: bool,
        fmt: str | None,
        noqa: bool,
    ) -> None:
        """Build a PO message."""
        self.filename = filename
        self.line = line
        # unescape strings
        msg = {k: escape_decode(v)[0].decode(charset) for k, v in msg.items()}  # ty: ignore[unresolved-attribute]
        # build messages as a list of tuples: (string, translation)
        self.messages = []
        if "msgid_plural" in msg:
            i = 0
            while True:
                key = f"msgstr[{i}]"
                if key not in msg:
                    break
                self.messages.append((msg["msgid_plural"], msg[key]))
                i += 1
        else:
            self.messages.append((msg.get("msgid", ""), msg.get("msgstr", "")))
        self.fuzzy = fuzzy
        self.fmt = fmt
        self.noqa = noqa

    def check_lines(self) -> list[PoReport]:
        """Check number of lines in string and translation.

        Return a list with errors detected.
        """
        errors = []
        for mid, mstr in self.messages:
            if not mid or not mstr:
                continue
            nb_id = count_lines(mid)
            nb_str = count_lines(mstr)
            if nb_id != nb_str:
                errors.append(
                    PoReport(
                        f"number of lines: {nb_id} in string, {nb_str} in translation",
                        "lines",
                        self.filename,
                        self.line,
                        mid,
                        mstr,
                    ),
                )
        return errors

    def check_punct(self, language: str) -> list[PoReport]:
        """Check punctuation at end of string.

        Return a list with errors detected.
        """
        errors = []
        for mid, mstr in self.messages:
            if not mid or not mstr:
                continue
            puncts = [
                (":", ":"),
                (";", ";"),
                (",", ","),
                ("...", "..."),
            ]
            # special symbols in some languages
            if language[:2] in ["ja", "zh"]:
                puncts.append((".", "。"))
            else:
                puncts.append((".", "."))
            for punctid, punctstr in puncts:
                len_pid = len(punctid)
                len_pstr = len(punctstr)
                if len(mid) < len_pid or len(mstr) < len_pstr:
                    continue
                match_id = mid.endswith(punctid)
                match_str = mstr.endswith(punctstr)
                if match_id and match_str:
                    break
                if match_id and not match_str:
                    errors.append(
                        PoReport(
                            f'end punctuation: "{punctid}" in string, "{punctstr}" not in translation',
                            "punct",
                            self.filename,
                            self.line,
                            mid,
                            mstr,
                        ),
                    )
                    break
                if not match_id and match_str:
                    errors.append(
                        PoReport(
                            f'end punctuation: "{punctstr}" in translation, "{punctid}" not in string',
                            "punct",
                            self.filename,
                            self.line,
                            mid,
                            mstr,
                        ),
                    )
                    break
        return errors

    def check_whitespace(self) -> list[PoReport]:
        """Check whitespace at beginning and end of string.

        Return a list with errors detected.
        """
        errors = []
        for mid, mstr in self.messages:
            if not mid or not mstr:
                continue
            # check whitespace at beginning of string
            if count_lines(mid) == 1:
                startin = len(mid) - len(mid.lstrip(" "))
                startout = len(mstr) - len(mstr.lstrip(" "))
                if startin != startout:
                    errors.append(
                        PoReport(
                            f"whitespace at beginning: {startin} in string, {startout} in translation",
                            "whitespace",
                            self.filename,
                            self.line,
                            mid,
                            mstr,
                        ),
                    )
            # check whitespace at end of string
            endin = len(mid) - len(mid.rstrip(" "))
            endout = len(mstr) - len(mstr.rstrip(" "))
            if endin != endout:
                errors.append(
                    PoReport(
                        f"whitespace at end: {endin} in string, {endout} in translation",
                        "whitespace",
                        self.filename,
                        self.line,
                        mid,
                        mstr,
                    ),
                )
        return errors

    def check_whitespace_eol(self) -> list[PoReport]:
        """Check trailing whitespace at the end of lines in a string.

        Return a list with errors detected.
        """
        errors = []
        for mid, mstr in self.messages:
            if not mid or not mstr:
                continue
            idlines = mid.split("\n")
            strlines = mstr.split("\n")
            if len(idlines) < 2 or len(idlines) != len(strlines):  # noqa: PLR2004
                continue
            for i, idline in enumerate(idlines):
                endin = len(idline) - len(idline.rstrip(" "))
                endout = len(strlines[i]) - len(strlines[i].rstrip(" "))
                if (endin > 0 or endout > 0) and endin != endout:
                    errors.append(
                        PoReport(
                            f"different whitespace at end of a line: {endin} in string, {endout} in translation",
                            "whitespace_eol",
                            self.filename,
                            self.line,
                            mid,
                            mstr,
                        ),
                    )
                    break
        return errors

    def check_spelling(self, spelling: str, checkers: list[SpellChecker]) -> list[PoReport]:
        """Check spelling.

        Return a list with errors detected.
        """
        errors: list[PoReport] = []
        if not checkers:
            return errors
        for mid, mstr in self.messages:
            if not mid or not mstr:
                continue
            text = mstr if spelling == "str" else mid
            if self.fmt:
                text = replace_formatters(text, self.fmt)
            checkers[0].set_text(text)
            misspelled = []
            for err in checkers[0]:
                misspelled_word = True
                for spell_checker in checkers[1:]:
                    if spell_checker.check(err.word):
                        misspelled_word = False
                        break
                if misspelled_word:
                    misspelled.append(err.word)
            if misspelled:
                errors.append(
                    PoReport(
                        misspelled,
                        "spelling-" + spelling,
                        self.filename,
                        self.line,
                        mid,
                        mstr,
                    ),
                )
        return errors


class Checker:
    """Messages checker."""

    def __init__(self) -> None:
        """Initialize checker."""
        self.numline = 0
        self.numline_msgid = 0
        self.fuzzy = False
        self.msgfuzzy = False
        self.noqa = False
        self.msgnoqa = False
        self.fmt: str | None = None
        self.msgfmt: str | None = None
        self.msg: dict[str, str] = {}
        self.msgcurrent = ""
        self.oldmsgcurrent = ""

    def check_line(self, line: str) -> tuple[int, bool, str | None, bool, dict[str, str]] | None:
        """Check a line of a PO file."""
        message = None
        self.numline += 1
        if not line:
            return None
        if line.startswith("#,"):
            self.fuzzy = "fuzzy" in line
            match = re.search(r"([a-z-]+)-format", line, re.IGNORECASE)
            self.fmt = match.group(1) if match else None
        if line.startswith("#"):
            self.noqa = self.noqa or "noqa" in line
            return None
        if line.startswith("msg"):
            match = re.match(r"([a-zA-Z0-9-_]+(\[\d+\])?)[ \t](.*)", line)
            if match:
                self.oldmsgcurrent = self.msgcurrent
                self.msgcurrent = match.group(1)
                line = match.group(3)
                if self.msgcurrent == "msgid":
                    if self.oldmsgcurrent.startswith("msgstr"):
                        message = (
                            self.numline_msgid,
                            self.msgfuzzy,
                            self.msgfmt,
                            self.msgnoqa,
                            self.msg,
                        )
                    self.msgfuzzy = self.fuzzy
                    self.msgnoqa = self.noqa
                    self.fuzzy = False
                    self.noqa = False
                    self.msgfmt = self.fmt
                    self.fmt = None
                    self.msg = {}
                    self.numline_msgid = self.numline
        if self.msgcurrent and line.startswith('"'):
            self.msg[self.msgcurrent] = self.msg.get(self.msgcurrent, "") + line[1:-1]
        return message

    def last_check(self) -> tuple[int, bool, str | None, bool, dict[str, str]] | None:
        """Consume the last message (after all lines were read)."""
        if self.msgcurrent.startswith("msgstr"):
            return (
                self.numline_msgid,
                self.msgfuzzy,
                self.msgfmt,
                self.msgnoqa,
                self.msg,
            )
        return None


class PoFile:
    """A gettext file.

    It includes methods to read the file, and perform checks on the translations.
    """

    def __init__(self, filename: str) -> None:
        """Initialize PO file."""
        self.filename = str(Path(filename).resolve())
        self.props: dict[str, Any] = {
            "language": "",
            "language_numline": 0,
            "charset": "utf-8",
        }
        self.msgs: list[PoMessage] = []

    def _add_message(self, numline_msgid: int, fuzzy: bool, fmt: str | None, noqa: bool, msg: dict[str, str]) -> None:
        """Add a message from PO file in list of messages."""
        if "msgid" in msg and not msg["msgid"]:
            # find file language/charset in properties
            # (first string without msgid)
            match = re.search(
                r"language: ([a-zA-Z-_]+)",
                msg.get("msgstr", ""),
                re.IGNORECASE,
            )
            if match:
                self.props["language"] = match.group(1)
                self.props["language_numline"] = numline_msgid
            match = re.search(
                r"charset=([a-zA-Z0-9-_]+)",
                msg.get("msgstr", ""),
                re.IGNORECASE,
            )
            if match:
                self.props["charset"] = match.group(1)
        self.msgs.append(
            PoMessage(
                self.filename,
                numline_msgid,
                msg,
                self.props["charset"],
                fuzzy,
                fmt,
                noqa,
            ),
        )

    def read(self) -> None:
        """Read messages in PO file."""
        self.msgs = []
        checker = Checker()
        with Path(self.filename).open("r", encoding="utf-8", errors="ignore") as po_file:
            for line in po_file:
                message = checker.check_line(line.strip())
                if message:
                    self._add_message(*message)
        message = checker.last_check()
        if message:
            self._add_message(*message)

    def compile(self) -> tuple[str, int]:
        """Compile PO file (with msgfmt -c).

        Return a tuple: (output, return code).
        """
        output = ""
        try:
            output = subprocess.check_output(  # noqa: S603
                ["msgfmt", "-c", "-o", "/dev/null", self.filename],  # noqa: S607
                stderr=subprocess.STDOUT,
            ).decode("utf-8", errors="replace")
        except subprocess.CalledProcessError as exc:
            return (exc.output.decode("utf-8", errors="replace"), exc.returncode)
        return (output, 0)


class PoCheck:
    """Perform checks on a gettext file."""

    def __init__(self) -> None:
        """Initialize PO checker."""
        # checks to perform
        self.checks = {
            "compile": True,
            "fuzzy": False,
            "check_noqa": False,
            "lines": True,
            "punct": True,
            "whitespace": True,
            "whitespace_eol": True,
            "extract": False,
            "error_on_fuzzy": False,
        }
        # spelling options
        self.spelling: str | None = None
        self.dicts: str | None = None
        self.extra_checkers: list[SpellChecker] = []
        self.pwl: str | None = None

    def __repr__(self) -> str:
        """Return PO checker as string."""
        return f"checks: {self.checks}, dicts: {self.dicts}, extra_checkers: {self.extra_checkers}"

    def set_check(self, check: str, state: bool = True) -> None:
        """Enable/disable a specific check."""
        if check in self.checks:
            self.checks[check] = state

    def set_spelling_options(self, spelling: str | None, dicts: str | None, pwl_files: list[str]) -> None:
        """Set spelling options."""
        self.spelling = spelling
        self.dicts = dicts
        self.pwl = get_concatenated_files(pwl_files)

        # build extra checkers with dicts
        self.extra_checkers = []
        if dicts:
            for lang in dicts.split(","):
                try:
                    _dict = Dict(lang)
                    self.extra_checkers.append(SpellChecker(_dict))
                except DictNotFoundError:  # noqa: PERF203
                    print(f'WARNING: enchant dictionary not found for language "{lang}"')

    def _get_language_checker(self, po_file: PoFile, reports: list[PoReport]) -> list[SpellChecker]:
        """Get checker for PO file language."""
        checker = []
        if self.spelling:
            lang = po_file.props["language"] if self.spelling == "str" else "en"
            try:
                if self.pwl:
                    with tempfile.NamedTemporaryFile() as tmp_file:
                        tmp_file.write(self.pwl.encode("utf-8"))
                        tmp_file.flush()
                        _dict = DictWithPWL(lang, tmp_file.name)
                else:
                    _dict = DictWithPWL(lang, None)  # ty: ignore[invalid-argument-type]
                checker.append(SpellChecker(_dict))
            except DictNotFoundError:
                reports.append(
                    PoReport(
                        f'enchant dictionary not found for language "{lang}"',
                        "dict",
                        po_file.filename,
                        po_file.props["language_numline"],
                    ),
                )
                checker = []
            except OSError as exc:
                reports.append(
                    PoReport(
                        str(exc),
                        "pwl",
                        po_file.filename,
                        po_file.props["language_numline"],
                    ),
                )
                checker = []
        return checker

    def check_msg(
        self,
        po_file: PoFile,
        checker: list[SpellChecker],
        msg: PoMessage,
        reports: list[PoReport],
    ) -> None:
        """Check one message."""
        if self.checks["extract"]:
            for mid, mstr in msg.messages:
                if mid and mstr:
                    reports.append(PoReport(mstr, "extract"))
        else:
            if self.checks["lines"]:
                reports += msg.check_lines()
            if self.checks["punct"]:
                reports += msg.check_punct(po_file.props["language"])
            if self.checks["whitespace"]:
                reports += msg.check_whitespace()
            if self.checks["whitespace_eol"]:
                reports += msg.check_whitespace_eol()
            if self.spelling:
                reports += msg.check_spelling(self.spelling, checker + self.extra_checkers)

    def check_pofile(self, po_file: PoFile) -> list[PoReport]:
        """Check translations in one PO file.

        Return a list of PoReport objects.
        """
        reports: list[PoReport] = []

        # build list of checkers (if spelling is enabled)
        checker = self._get_language_checker(po_file, reports)

        # check all messages
        check_error_on_fuzzy = self.checks["error_on_fuzzy"]
        check_fuzzy = self.checks["fuzzy"]
        check_noqa = self.checks["check_noqa"]
        for msg in po_file.msgs:
            if check_error_on_fuzzy and msg.fuzzy:
                mid = msg.messages[0][0] if msg.messages else ""
                mstr = msg.messages[0][1] if msg.messages else ""
                reports.append(
                    PoReport(
                        "fuzzy string",
                        "fuzzy",
                        po_file.filename,
                        msg.line,
                        mid,
                        mstr,
                        fuzzy=True,
                    ),
                )
            if msg.noqa and not check_noqa:
                continue
            if msg.fuzzy and not check_fuzzy:
                continue
            self.check_msg(po_file, checker, msg, reports)

        return reports

    def check_file(self, filename: str) -> PoFileReport :
        """Check compilation and translations in a PO file."""
        po_file = PoFile(filename)
        report = PoFileReport(po_file.filename)
        # read the file
        try:
            po_file.read()
        except OSError as exc:
            report.append(PoReport(str(exc), "read", po_file.filename))
            return report
        # compile the file (except if disabled)
        compile_rc = 0
        if self.checks["compile"]:
            compile_output, compile_rc = po_file.compile()
        if compile_rc != 0:
            # compilation failed
            report.append(PoReport(compile_output, "compile", po_file.filename))
            return report
        # compilation OK
        report.extend(self.check_pofile(po_file))
        return report

    def check_files(self, files: list[str]) -> list[PoFileReport]:
        """Check compilation and translations in PO files.

        Return a list of tuples: (filename, [PoReport, PoReport, ...]).
        """
        result: list[PoFileReport] = []
        for path in files:
            if Path(path).is_dir():
                for root, _, filenames in os.walk(path):
                    result.extend([
                        self.check_file(str(Path(root) / filename))
                        for filename in filenames
                        if filename.endswith(".po")
                    ])
            else:
                result.append(self.check_file(path))
        return result
