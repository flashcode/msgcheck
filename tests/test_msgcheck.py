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

"""Tests on msgcheck."""

from pathlib import Path

import pytest

from msgcheck.po import PoCheck, PoFile, PoMessage
from msgcheck.utils import replace_formatters


def local_path(filename: str) -> str:
    """Return path to a file in the "tests" directory."""
    return str(Path(__file__).resolve().parent / filename)


def test_compilation() -> None:
    """Test compilation of gettext files."""
    # valid file
    assert PoFile(local_path("fr.po")).compile()[1] == 0

    # invalid file
    assert PoFile(local_path("fr_compile.po")).compile()[1] == 1


def test_read() -> None:
    """Test read of gettext files."""
    # valid file
    try:
        PoFile(local_path("fr.po")).read()
    except OSError:
        pytest.fail("Read error on a valid file.")

    # non-existing file
    with pytest.raises(FileNotFoundError):
        PoFile(local_path("fr_does_not_exist.po")).read()


def test_extract() -> None:
    """Test extract on a gettext file."""
    po_check = PoCheck()
    po_check.set_check("extract")
    result = po_check.check_files([local_path("fr.po")])
    assert len(result) == 1
    assert "fr.po" in result[0].filename
    assert len(result[0]) == 3

    report = result[0][0]
    assert report.message == "Ceci est un test.\n"
    assert report.idmsg == "extract"
    assert report.filename == "-"
    assert report.line == 0
    assert report.mid == ""
    assert report.mstr == ""
    assert report.fuzzy is False
    assert report.to_string() == "Ceci est un test.\n\n---"

    report = result[0][1]
    assert report.message == "Test sur deux lignes.\nLigne 2."
    assert report.idmsg == "extract"
    assert report.filename == "-"
    assert report.line == 0
    assert report.mid == ""
    assert report.mstr == ""
    assert report.fuzzy is False
    assert report.to_string() == "Test sur deux lignes.\nLigne 2.\n---"

    report = result[0][2]
    assert report.message == " erreur : %s"  # noqa: RUF001
    assert report.idmsg == "extract"
    assert report.filename == "-"
    assert report.line == 0
    assert report.mid == ""
    assert report.mstr == ""
    assert report.fuzzy is False
    assert report.to_string() == " erreur : %s\n---"  # noqa: RUF001


def test_checks() -> None:
    """Test checks on gettext files."""
    po_check = PoCheck()
    result = po_check.check_files([local_path("fr.po"), local_path("fr_errors.po")])

    # be sure we have 2 files in result
    assert len(result) == 2

    # first file has no errors
    assert not result[0]

    # second file has 10 errors
    assert len(result[1]) == 9

    # check first error
    report = result[1][0]
    assert report.message == "number of lines: 2 in string, 1 in translation"
    assert report.idmsg == "lines"
    assert "fr_errors.po" in report.filename
    assert report.line == 44
    assert report.mid == "Test 1 on two lines.\nLine 2."
    assert report.mstr == "Test 1 sur deux lignes."
    assert report.fuzzy is False
    assert "fr_errors.po:44: [lines] number of lines: 2 in string, 1 in translation" in report.to_string()

    # check last error
    report = result[1][8]
    expected = "different whitespace at end of a line: 1 in string, 0 in translation"
    assert report.message == expected
    assert report.idmsg == "whitespace_eol"
    assert "fr_errors.po" in report.filename
    assert report.line == 76
    assert report.mid == "Line 1. \nLine 2."
    assert report.mstr == "Ligne 1.\nLigne 2."
    assert report.fuzzy is False

    # check number of errors by type
    errors: dict[str, int] = {}
    for report in result[1]:
        errors[report.idmsg] = errors.get(report.idmsg, 0) + 1
    assert errors["lines"] == 2
    assert errors["punct"] == 1
    assert errors["whitespace"] == 4
    assert errors["whitespace_eol"] == 2


def test_checks_fuzzy() -> None:
    """Test checks on a gettext file including fuzzy strings."""
    po_check = PoCheck()
    po_check.set_check("fuzzy")
    result = po_check.check_files([local_path("fr_errors.po")])

    # be sure we have one file in result
    assert len(result) == 1

    # the file has 10 errors (with the fuzzy string)
    assert len(result[0]) == 10


def test_error_on_fuzzy() -> None:
    """Test error_on_fuzzy option that raises an error when fuzzy strings are found."""
    po_check = PoCheck()
    # disable all tests and enable only "error_on_fuzzy"
    po_check.checks = dict.fromkeys(po_check.checks, False)
    po_check.set_check("error_on_fuzzy")
    result = po_check.check_files([local_path("fr_errors.po")])

    # be sure we have one file in result
    assert len(result) == 1

    # the file has 1 fuzzy string
    assert len(result[0]) == 1

    # check the error report
    report = result[0][0]
    assert report.idmsg == "fuzzy"
    assert report.message == "fuzzy string"
    assert report.fuzzy is True
    assert "fr_errors.po" in report.filename
    assert report.line == 58  # Line where the fuzzy string starts
    assert report.mid == "Tested 3"
    assert report.mstr == "Testé 3."


def test_error_on_fuzzy_no_fuzzy_strings() -> None:
    """Test error_on_fuzzy option when there are no fuzzy strings."""
    po_check = PoCheck()
    # disable all tests and enable only "error_on_fuzzy"
    po_check.checks = dict.fromkeys(po_check.checks, False)
    po_check.set_check("error_on_fuzzy")
    result = po_check.check_files([local_path("fr.po")])

    # be sure we have one file in result
    assert len(result) == 1

    # the file has 10 errors (no fuzzy strings)
    assert len(result[0]) == 0


def test_checks_noqa() -> None:
    """Test checks on a gettext file including `noqa`-commented lines."""
    po_check = PoCheck()
    po_check.set_check("check_noqa")
    result = po_check.check_files([local_path("fr_errors.po")])

    # be sure we have one file in result
    assert len(result) == 1

    # the file has 10 errors (including `noqa`-commented lines)
    assert len(result[0]) == 10


def test_replace_fmt_c() -> None:
    """Test removal of formatters in a C string."""
    assert replace_formatters("%s", "c") == ""
    assert replace_formatters("%%", "c") == "%"
    assert replace_formatters("%.02f", "c") == ""
    assert replace_formatters("%!%s%!", "c") == "%!%!"
    assert replace_formatters("%.02!", "c") == "%.02!"
    assert replace_formatters("%.3fThis is a %stest", "c") == "This is a test"
    assert replace_formatters("%.3fTest%s%d%%%.03f%luhere% s", "c") == "Test%here"


def test_replace_fmt_python() -> None:
    """Test removal of formatters in a python string."""
    assert replace_formatters("%s", "python") == ""
    assert replace_formatters("%b", "python") == ""
    assert replace_formatters("%%", "python") == "%"
    assert replace_formatters("%.02f", "python") == ""
    assert replace_formatters("%(sth)s", "python") == ""
    assert replace_formatters("%(sth)02f", "python") == ""


def test_replace_fmt_python_brace() -> None:
    """Test removal of formatters in a python brace string."""
    conditions = (
        (
            "First, thou shalt count to {0}",
            "First, thou shalt count to ",
            "References first positional argument",
        ),
        (
            "Bring me a {}",
            "Bring me a ",
            "Implicitly references the first positional argument",
        ),
        (
            "From {} to {}",
            "From  to ",
            'Same as "From {0} to {1}"',
        ),
        (
            "My quest is {name}",
            "My quest is ",
            "References keyword argument 'name'",
        ),
        (
            "Weight in tons {0.weight}",
            "Weight in tons ",
            "'weight' attribute of first positional arg",
        ),
        (
            "Units destroyed: {players[0]}",
            "Units destroyed: ",
            "First element of keyword argument 'players'.",
        ),
    )
    for condition in conditions:
        assert replace_formatters(condition[0], "python-brace") == condition[1], condition[2]


def test_spelling_id() -> None:
    """Test spelling on source messages (English) of gettext files."""
    po_check = PoCheck()
    pwl_files = [local_path("pwl1.txt")]
    po_check.set_spelling_options("id", None, pwl_files)
    result = po_check.check_files([local_path("fr_spelling_id.po")])

    # be sure we have 1 file in result
    assert len(result) == 1

    # the file has 2 spelling errors: "Thsi" and "errro"
    report = result[0]
    assert len(report) == 3
    for i, word in enumerate(("Thsi", "testtwo", "errro")):
        assert report[i].idmsg == "spelling-id"
        assert isinstance(report[i].message, list)
        assert len(report[i].message) == 1
        assert report[i].message[0] == word
        assert report[i].get_misspelled_words() == [word]


def test_spelling_id_multilpe_pwl() -> None:
    """Test spelling on source messages (English) of gettext files using multiple personal word lists."""
    po_check = PoCheck()
    pwl_files = [
        local_path("pwl1.txt"),
        local_path("pwl2.txt"),
    ]
    po_check.set_spelling_options("id", None, pwl_files)
    result = po_check.check_files([local_path("fr_spelling_id.po")])

    # be sure we have 1 file in result
    assert len(result) == 1

    # the file has 2 spelling errors: "Thsi" and "errro"
    report = result[0]
    assert len(report) == 2
    for i, word in enumerate(("Thsi", "errro")):
        assert report[i].idmsg == "spelling-id"
        assert isinstance(report[i].message, list)
        assert len(report[i].message) == 1
        assert report[i].message[0] == word
        assert report[i].get_misspelled_words() == [word]


def test_spelling_str() -> None:
    """Test spelling on translated messages of gettext files."""
    po_check = PoCheck()
    pwl_files = [local_path("pwl1.txt")]
    po_check.set_spelling_options("str", None, pwl_files)
    result = po_check.check_files([local_path("fr_spelling_str.po"), local_path("fr_language.po")])

    # be sure we have 2 files in result
    assert len(result) == 2

    # first file has 3 spelling errors: "CecX", "aabbcc" and "xxyyzz"
    report = result[0]
    assert len(report) == 4
    for i, word in enumerate(("testtwo", "CecX", "aabbcc", "xxyyzz")):
        assert report[i].idmsg == "spelling-str"
        assert isinstance(report[i].message, list)
        assert len(report[i].message) == 1
        assert report[i].message[0] == word
        assert report[i].get_misspelled_words() == [word]

    # second file has 1 error: dict/language "xyz" not found
    report = result[1]
    assert len(report) == 1
    assert report[0].idmsg == "dict"


def test_spelling_str_multiple_pwl() -> None:
    """Test spelling on translated messages of gettext files using multiple personal word lists."""
    po_check = PoCheck()
    pwl_files = [
        local_path("pwl1.txt"),
        local_path("pwl2.txt"),
    ]
    po_check.set_spelling_options("str", None, pwl_files)
    result = po_check.check_files([local_path("fr_spelling_str.po"), local_path("fr_language.po")])

    # be sure we have 2 files in result
    assert len(result) == 2

    # first file has 3 spelling errors: "CecX", "aabbcc" and "xxyyzz"
    report = result[0]
    assert len(report) == 3
    for i, word in enumerate(("CecX", "aabbcc", "xxyyzz")):
        assert report[i].idmsg == "spelling-str"
        assert isinstance(report[i].message, list)
        assert len(report[i].message) == 1
        assert report[i].message[0] == word
        assert report[i].get_misspelled_words() == [word]

    # second file has 1 error: dict/language "xyz" not found
    report = result[1]
    assert len(report) == 1
    assert report[0].idmsg == "dict"


def test_spelling_bad_dict() -> None:
    """Test spelling with a bad dict option."""
    po_check = PoCheck()
    po_check.set_spelling_options("str", "xxx", [])
    assert not po_check.extra_checkers


def test_spelling_bad_pwl() -> None:
    """Test spelling with a bad pwl option."""
    po_check = PoCheck()
    pwl_files = [local_path("pwl_does_not_exist.txt")]
    with pytest.raises(FileNotFoundError):
        po_check.set_spelling_options("str", None, pwl_files)


@pytest.mark.parametrize(
    ("language", "msgid", "msgstr", "error_message"),
    [
        (
            "ja",
            "Should not raise an error.",
            "エラーが発生しないようにしてください。",
            "",
        ),
        (
            "ja",
            "Should raise an error",
            "エラーを発生させる必要があります。",
            'end punctuation: "。" in translation, "." not in string',
        ),
        (
            "ja",
            "Should raise an error.",
            "エラーを発生させる必要があります",
            'end punctuation: "." in string, "。" not in translation',
        ),
        (
            "ja",
            "Should raise an error.",
            "エラーを発生させる必要があります.",
            'end punctuation: "." in string, "。" not in translation',
        ),
        (
            "zh-Hans",
            "Should not raise an error.",
            "不应引起错误。",
            "",
        ),
        (
            "zh-Hans",
            "Should raise an error",
            "应该会出现一个错误。",
            'end punctuation: "。" in translation, "." not in string',
        ),
        (
            "zh-Hans",
            "Should raise an error.",
            "应该会出现一个错误",
            'end punctuation: "." in string, "。" not in translation',
        ),
        (
            "zh-Hans",
            "Should raise an error.",
            "应该会出现一个错误.",
            'end punctuation: "." in string, "。" not in translation',
        ),
    ],
)
def test_punct_full_stop_ja_zh(language: str, msgid: str, msgstr: str, error_message: str) -> None:
    """Test punctuation with non-latin full-stops."""
    msg = PoMessage("translation.po", 42, {}, "utf-8", False, None, False)
    msg.messages = [(msgid, msgstr)]
    errors = PoMessage.check_punct(msg, language)
    if error_message:
        assert error_message in errors[0].message
    else:
        assert not errors


def test_invalid_utf8() -> None:
    """Test checks on a file with invalid UTF-8 chars."""
    po_check = PoCheck()
    po_check.set_check("fuzzy")
    result = po_check.check_files([local_path("fr_invalid_utf8.po")])

    # be sure we have one file in result
    assert len(result) == 1

    # the file has no errors
    assert len(result[0]) == 0
