#!/usr/bin/env python3
#
# Copyright (C) 2009-2024 Sébastien Helleu <flashcode@flashtux.org>
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

from __future__ import print_function

from codecs import escape_decode
import os
import re
import subprocess  # nosec
import tempfile

# enchant module is optional, spelling is checked on demand
# (argument -s/--spell)
try:
    from enchant import Dict, DictWithPWL, DictNotFoundError
    from enchant.checker import SpellChecker
    ENCHANT_FOUND = True
except ImportError:
    ENCHANT_FOUND = False

from .utils import count_lines, replace_formatters


def get_concatenated_files(filenames):
    """Return concatenated content of multiple files."""
    if not filenames:
        return None
    content = []
    for filename in filenames:
        with open(filename, "rb") as _file:
            content.append(_file.read().decode("utf-8"))
    return "\n".join(content)


class PoReport:  # pylint: disable=too-few-public-methods
    """A message in report (commonly an error in detected in gettext file)."""

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        message,
        idmsg="",
        filename="-",
        line=0,
        mid="",
        mstr="",
        fuzzy=False,
    ):
        self.message = message
        self.idmsg = idmsg
        self.filename = filename
        self.line = line
        self.mid = mid
        self.mstr = mstr
        self.fuzzy = fuzzy

    def __repr__(self):
        if self.idmsg == "extract":
            return self.message + "\n---"
        if self.idmsg == "compile":
            return f'{"=" * 70}\n{self.message}'
        is_list = isinstance(self.message, list)
        count = f"({len(self.message)})" if is_list else ""
        str_fuzzy = "(fuzzy) " if self.fuzzy else ""
        str_msg = ", ".join(self.message) if is_list else self.message
        msg = (
            f'{"=" * 70}\n{self.filename}:{self.line}: '
            f"[{self.idmsg}{count}] {str_fuzzy}{str_msg}"
        )
        if self.mid:
            msg += "\n---\n" + self.mid
        if self.mstr:
            msg += "\n---\n" + self.mstr
        return msg

    def get_misspelled_words(self):
        """Return list of misspelled words."""
        return self.message if isinstance(self.message, list) else []


class PoMessage:
    """
    A message from a gettext file. It is stored as a list of tuples
    (string, translation).
    The list usually have one element, except if the plural form is
    used.

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

    # pylint: disable=too-many-arguments
    def __init__(self, filename, line, msg, charset, fuzzy, fmt, noqa):
        """Build a PO message."""
        self.filename = filename
        self.line = line
        # unescape strings
        msg = {k: escape_decode(v)[0].decode(charset) for k, v in msg.items()}
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
            self.messages.append(
                (msg.get("msgid", ""), msg.get("msgstr", ""))
            )
        self.fuzzy = fuzzy
        self.fmt = fmt
        self.noqa = noqa

    def check_lines(self):
        """
        Check number of lines in string and translation.
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
                        f"number of lines: {nb_id} in string, "
                        f"{nb_str} in translation",
                        "lines",
                        self.filename,
                        self.line,
                        mid,
                        mstr,
                    )
                )
        return errors

    def check_punct(self, language):
        """
        Check punctuation at end of string.
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
                            f"end punctuation: \"{punctid}\" in string, "
                            f"\"{punctstr}\" not in translation",
                            "punct",
                            self.filename,
                            self.line,
                            mid,
                            mstr,
                        )
                    )
                    break
                if not match_id and match_str:
                    errors.append(
                        PoReport(
                            f"end punctuation: \"{punctstr}\" in "
                            f"translation, \"{punctid}\" not in string",
                            "punct",
                            self.filename,
                            self.line,
                            mid,
                            mstr,
                        )
                    )
                    break
        return errors

    def check_whitespace(self):
        """
        Check whitespace at beginning and end of string.
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
                            f"whitespace at beginning: {startin} in "
                            f"string, {startout} in translation",
                            "whitespace",
                            self.filename,
                            self.line,
                            mid,
                            mstr,
                        )
                    )
            # check whitespace at end of string
            endin = len(mid) - len(mid.rstrip(" "))
            endout = len(mstr) - len(mstr.rstrip(" "))
            if endin != endout:
                errors.append(
                    PoReport(
                        f"whitespace at end: {endin} in string, "
                        f"{endout} in translation",
                        "whitespace",
                        self.filename,
                        self.line,
                        mid,
                        mstr,
                    )
                )
        return errors

    def check_whitespace_eol(self):
        """
        Check trailing whitespace at the end of lines in a string.
        Return a list with errors detected.
        """
        errors = []
        for mid, mstr in self.messages:
            if not mid or not mstr:
                continue
            idlines = mid.split("\n")
            strlines = mstr.split("\n")
            if len(idlines) < 2 or len(idlines) != len(strlines):
                continue
            for i, idline in enumerate(idlines):
                endin = len(idline) - len(idline.rstrip(" "))
                endout = len(strlines[i]) - len(strlines[i].rstrip(" "))
                if (endin > 0 or endout > 0) and endin != endout:
                    errors.append(
                        PoReport(
                            f"different whitespace at end of a line: {endin} "
                            f"in string, {endout} in translation",
                            "whitespace_eol",
                            self.filename,
                            self.line,
                            mid,
                            mstr,
                        )
                    )
                    break
        return errors

    def check_spelling(self, spelling, checkers):
        """
        Check spelling.
        Return a list with errors detected.
        """
        errors = []
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
                    )
                )
        return errors


class Checker:  # pylint: disable=too-many-instance-attributes
    """Messages checker."""

    def __init__(self):
        self.numline = 0
        self.numline_msgid = 0
        self.fuzzy = False
        self.msgfuzzy = False
        self.noqa = False
        self.msgnoqa = False
        self.fmt = None
        self.msgfmt = None
        self.msg = {}
        self.msgcurrent = ""
        self.oldmsgcurrent = ""

    def check_line(self, line):
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
            self.msg[self.msgcurrent] = (
                self.msg.get(self.msgcurrent, "") + line[1:-1]
            )
        return message

    def last_check(self):
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
    """
    A gettext file. It includes methods to read the file, and perform
    checks on the translations.
    """

    def __init__(self, filename):
        self.filename = os.path.abspath(filename)
        self.props = {
            "language": "",
            "language_numline": 0,
            "charset": "utf-8",
        }
        self.msgs = []

    # pylint: disable=too-many-arguments
    def _add_message(self, numline_msgid, fuzzy, fmt, noqa, msg):
        """
        Add a message from PO file in list of messages.
        """
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
            )
        )

    def read(self):  # pylint: disable=too-many-locals
        """
        Read messages in PO file.
        """
        self.msgs = []
        checker = Checker()
        with open(self.filename, "r", encoding="utf-8") as po_file:
            for line in po_file:
                message = checker.check_line(line.strip())
                if message:
                    self._add_message(*message)
        message = checker.last_check()
        if message:
            self._add_message(*message)

    def compile(self):
        """
        Compile PO file (with msgfmt -c).
        Return a tuple: (output, return code).
        """
        output = ""
        try:
            output = subprocess.check_output(  # nosec
                ["msgfmt", "-c", "-o", "/dev/null", self.filename],
                stderr=subprocess.STDOUT,
            )
        except subprocess.CalledProcessError as exc:
            return (exc.output, exc.returncode)
        return (output, 0)


class PoCheck:
    """Perform checks on a gettext file."""

    def __init__(self):
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
        }

        # spelling options
        self.spelling = None
        self.dicts = None
        self.extra_checkers = []
        self.pwl = None

    def __repr__(self):
        return (
            f"checks: {self.checks}, dicts: {self.dicts}, "
            f"extra_checkers: {self.extra_checkers}"
        )

    def set_check(self, check, state):
        """Enable/disable a specific check."""
        if check in self.checks:
            self.checks[check] = bool(state)

    def set_spelling_options(self, spelling, dicts, pwl_files):
        """Set spelling options."""
        self.spelling = spelling
        self.dicts = dicts
        self.pwl = get_concatenated_files(pwl_files)

        # build extra checkers with dicts
        self.extra_checkers = []
        if dicts:
            if not ENCHANT_FOUND:
                raise ImportError(
                    "Enchant module not found (please install \"pyenchant\")"
                )
            for lang in dicts.split(","):
                try:
                    _dict = Dict(lang)
                    self.extra_checkers.append(SpellChecker(_dict))
                except DictNotFoundError:
                    print(
                        f"WARNING: enchant dictionary not found for "
                        f"language \"{lang}\""
                    )

    def _get_language_checker(self, po_file, reports):
        """Get checker for PO file language."""
        checker = []
        if self.spelling:
            if not ENCHANT_FOUND:
                raise ImportError(
                    "Enchant module not found (please install \"pyenchant\")"
                )
            lang = (
                po_file.props["language"] if self.spelling == "str" else "en"
            )
            try:
                if self.pwl:
                    with tempfile.NamedTemporaryFile() as tmp_file:
                        tmp_file.write(self.pwl.encode("utf-8"))
                        tmp_file.flush()
                        _dict = DictWithPWL(lang, tmp_file.name)
                else:
                    _dict = DictWithPWL(lang, None)
                checker.append(SpellChecker(_dict))
            except DictNotFoundError:
                reports.append(
                    PoReport(
                        f"enchant dictionary not found for language "
                        f"\"{lang}\"",
                        "dict",
                        po_file.filename,
                        po_file.props["language_numline"],
                    )
                )
                checker = []
            except IOError as exc:
                reports.append(
                    PoReport(
                        str(exc),
                        "pwl",
                        po_file.filename,
                        po_file.props["language_numline"],
                    )
                )
                checker = []
        return checker

    def check_msg(self, po_file, checker, msg, reports):
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
                reports += msg.check_spelling(
                    self.spelling, checker + self.extra_checkers
                )

    def check_pofile(self, po_file):
        """
        Check translations in one PO file.
        Return a list of PoReport objects.
        """

        reports = []

        # build list of checkers (if spelling is enabled)
        checker = self._get_language_checker(po_file, reports)

        # check all messages
        check_fuzzy = self.checks["fuzzy"]
        check_noqa = self.checks["check_noqa"]
        for msg in po_file.msgs:
            if msg.noqa and not check_noqa:
                continue
            if msg.fuzzy and not check_fuzzy:
                continue
            self.check_msg(po_file, checker, msg, reports)

        return reports

    def check_files(self, files):
        """
        Check translations in PO files.
        Return a list of tuples: (filename, [PoReport, PoReport, ...]).
        """

        result = []

        for filename in files:
            po_file = PoFile(filename)
            # read the file
            try:
                po_file.read()
            except IOError as exc:
                result.append(
                    (
                        po_file.filename,
                        [PoReport(str(exc), "read", po_file.filename)],
                    )
                )
                continue
            # compile the file (except if disabled)
            compile_rc = 0
            if self.checks["compile"]:
                compile_output, compile_rc = po_file.compile()
            if compile_rc == 0:
                # compilation OK
                result.append((po_file.filename, self.check_pofile(po_file)))
            else:
                # compilation failed
                compile_output = bytes(compile_output).decode("utf-8")
                result.append(
                    (
                        po_file.filename,
                        [
                            PoReport(
                                compile_output, "compile", po_file.filename
                            )
                        ],
                    )
                )

        return result
