# -*- coding: utf-8 -*-
#
# Copyright (C) 2009-2020 Sébastien Helleu <flashcode@flashtux.org>
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
Tests on msgcheck.
"""

import os
import pytest

from msgcheck.po import PoFile, PoCheck
from msgcheck.utils import replace_formatters


def local_path(filename):
    """Return path to a file in the "tests" directory."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)


def test_compilation():
    """Test compilation of gettext files."""
    # valid file
    assert PoFile(local_path('fr.po')).compile()[1] == 0

    # invalid file
    assert PoFile(local_path('fr_compile.po')).compile()[1] == 1


def test_read():
    """Test read of gettext files."""
    # valid file
    try:
        PoFile(local_path('fr.po')).read()
    except IOError:
        pytest.fail('Read error on a valid file.')

    # non-existing file
    with pytest.raises(IOError):
        PoFile(local_path('fr_does_not_exist.po')).read()


def test_checks():
    """Test checks on gettext files."""
    po_check = PoCheck()
    result = po_check.check_files([local_path('fr.po'),
                                   local_path('fr_errors.po')])

    # be sure we have 2 files in result
    assert len(result) == 2

    # first file has no errors
    assert not result[0][1]

    # second file has 10 errors
    assert len(result[1][1]) == 10
    errors = {}
    for report in result[1][1]:
        errors[report.idmsg] = errors.get(report.idmsg, 0) + 1
    assert errors['lines'] == 2
    assert errors['punct'] == 2
    assert errors['whitespace'] == 4
    assert errors['whitespace_eol'] == 2


def test_checks_fuzzy():
    """Test checks on a gettext file including fuzzy strings."""
    po_check = PoCheck()
    po_check.set_check('fuzzy', True)
    result = po_check.check_files([local_path('fr_errors.po')])

    # be sure we have one file in result
    assert len(result) == 1

    # the file has 11 errors (with the fuzzy string)
    assert len(result[0][1]) == 11


def test_checks_noqa():
    """Test checks on a gettext file ignoring `noqa`-commented lines."""
    po_check = PoCheck()
    po_check.set_check('skip_noqa', True)
    result = po_check.check_files([local_path('fr_errors.po')])

    # be sure we have one file in result
    assert len(result) == 1

    # the file has 9 errors (`noqa` was skipped)
    assert len(result[0][1]) == 9


def test_replace_fmt_c():
    """Test removal of formatters in a C string."""
    assert replace_formatters('%s', 'c') == ''
    assert replace_formatters('%%', 'c') == '%'
    assert replace_formatters('%.02f', 'c') == ''
    assert replace_formatters('%!%s%!', 'c') == '%!%!'
    assert replace_formatters('%.02!', 'c') == '%.02!'
    assert replace_formatters('%.3fThis is a %stest', 'c') == 'This is a test'
    assert replace_formatters('%.3fTest%s%d%%%.03f%luhere% s', 'c') == \
        'Test%here'


def test_replace_fmt_python():
    """Test removal of formatters in a python string."""
    # str.__mod__()
    assert replace_formatters('%s', 'python') == ''
    assert replace_formatters('%b', 'python') == ''
    assert replace_formatters('%%', 'python') == '%'
    assert replace_formatters('%.02f', 'python') == ''
    assert replace_formatters('%(sth)s', 'python') == ''
    assert replace_formatters('%(sth)02f', 'python') == ''


def test_replace_fmt_python_brace():
    """Test removal of formatters in a python brace string."""
    # str.format()
    conditions = (
        ('First, thou shalt count to {0}',
         'First, thou shalt count to ',
         'References first positional argument'),
        ('Bring me a {}',
         'Bring me a ',
         'Implicitly references the first positional argument'),
        ('From {} to {}',
         'From  to ',
         'Same as "From {0} to {1}"'),
        ('My quest is {name}',
         'My quest is ',
         'References keyword argument \'name\''),
        ('Weight in tons {0.weight}',
         'Weight in tons ',
         '\'weight\' attribute of first positional arg'),
        ('Units destroyed: {players[0]}',
         'Units destroyed: ',
         'First element of keyword argument \'players\'.'),
    )
    for condition in conditions:
        assert replace_formatters(condition[0], 'python-brace') == \
            condition[1], condition[2]


def test_spelling_id():
    """Test spelling on source messages (English) of gettext files."""
    po_check = PoCheck()
    pwl_files = [local_path('pwl1.txt')]
    po_check.set_spelling_options('id', None, pwl_files)
    result = po_check.check_files([local_path('fr_spelling_id.po')])

    # be sure we have 1 file in result
    assert len(result) == 1

    # the file has 2 spelling errors: "Thsi" and "errro"
    errors = result[0][1]
    assert len(errors) == 3
    for i, word in enumerate(('Thsi', 'testtwo', 'errro')):
        assert errors[i].idmsg == 'spelling-id'
        assert isinstance(errors[i].message, list)
        assert len(errors[i].message) == 1
        assert errors[i].message[0] == word


def test_spelling_id_multilpe_pwl():
    """
    Test spelling on source messages (English) of gettext files
    using multiple personal word lists.
    """
    po_check = PoCheck()
    pwl_files = [
        local_path('pwl1.txt'),
        local_path('pwl2.txt'),
    ]
    po_check.set_spelling_options('id', None, pwl_files)
    result = po_check.check_files([local_path('fr_spelling_id.po')])

    # be sure we have 1 file in result
    assert len(result) == 1

    # the file has 2 spelling errors: "Thsi" and "errro"
    errors = result[0][1]
    assert len(errors) == 2
    for i, word in enumerate(('Thsi', 'errro')):
        assert errors[i].idmsg == 'spelling-id'
        assert isinstance(errors[i].message, list)
        assert len(errors[i].message) == 1
        assert errors[i].message[0] == word


def test_spelling_str():
    """Test spelling on translated messages of gettext files."""
    po_check = PoCheck()
    pwl_files = [local_path('pwl1.txt')]
    po_check.set_spelling_options('str', None, pwl_files)
    result = po_check.check_files([local_path('fr_spelling_str.po'),
                                   local_path('fr_language.po')])

    # be sure we have 2 files in result
    assert len(result) == 2

    # first file has 3 spelling errors: "CecX", "aabbcc" and "xxyyzz"
    errors = result[0][1]
    assert len(errors) == 4
    for i, word in enumerate(('testtwo', 'CecX', 'aabbcc', 'xxyyzz')):
        assert errors[i].idmsg == 'spelling-str'
        assert isinstance(errors[i].message, list)
        assert len(errors[i].message) == 1
        assert errors[i].message[0] == word

    # second file has 1 error: dict/language "xyz" not found
    errors = result[1][1]
    assert len(errors) == 1
    assert errors[0].idmsg == 'dict'


def test_spelling_str_multiple_pwl():
    """
    Test spelling on translated messages of gettext files
    using multiple personal word lists.
    """
    po_check = PoCheck()
    pwl_files = [
        local_path('pwl1.txt'),
        local_path('pwl2.txt'),
    ]
    po_check.set_spelling_options('str', None, pwl_files)
    result = po_check.check_files([local_path('fr_spelling_str.po'),
                                   local_path('fr_language.po')])

    # be sure we have 2 files in result
    assert len(result) == 2

    # first file has 3 spelling errors: "CecX", "aabbcc" and "xxyyzz"
    errors = result[0][1]
    assert len(errors) == 3
    for i, word in enumerate(('CecX', 'aabbcc', 'xxyyzz')):
        assert errors[i].idmsg == 'spelling-str'
        assert isinstance(errors[i].message, list)
        assert len(errors[i].message) == 1
        assert errors[i].message[0] == word

    # second file has 1 error: dict/language "xyz" not found
    errors = result[1][1]
    assert len(errors) == 1
    assert errors[0].idmsg == 'dict'


def test_spelling_bad_dict():
    """Test spelling with a bad dict option."""
    po_check = PoCheck()
    po_check.set_spelling_options('str', 'xxx', None)
    assert not po_check.extra_checkers


def test_spelling_bad_pwl():
    """Test spelling with a bad pwl option."""
    po_check = PoCheck()
    with pytest.raises(IOError):
        pwl_files = [local_path('pwl_does_not_exist.txt')]
        po_check.set_spelling_options('str', None, pwl_files)
