# -*- coding: utf-8 -*-
#
# Copyright (C) 2009-2017 Sébastien Helleu <flashcode@flashtux.org>
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
# along with msgcheck.  If not, see <http://www.gnu.org/licenses/>.
#

"""
Tests on msgcheck.
"""

import os
import unittest

from msgcheck.po import PoFile, PoCheck
from msgcheck.utils import replace_formatters


def local_path(filename):
    """Return path to a file in the "tests" directory."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)


# pylint: disable=too-many-public-methods
class TestMsgCheck(unittest.TestCase):
    """Tests on msgcheck."""

    def test_compilation(self):
        """Test compilation of gettext files."""
        # valid file
        self.assertEqual(PoFile(local_path('fr.po')).compile()[1], 0)

        # invalid file
        self.assertEqual(PoFile(local_path('fr_compile.po')).compile()[1], 1)

    def test_read(self):
        """Test read of gettext files."""
        # valid file
        try:
            PoFile(local_path('fr.po')).read()
        except IOError:
            self.fail('Read error on a valid file.')

        # non-existing file
        try:
            PoFile(local_path('fr_does_not_exist.po')).read()
        except IOError:
            pass  # this exception is expected
        else:
            self.fail('No problem when reading non-existing file!')

    def test_checks(self):
        """Test checks on gettext files."""
        po_check = PoCheck()
        result = po_check.check_files([local_path('fr.po'),
                                       local_path('fr_errors.po')])

        # be sure we have 2 files in result
        self.assertEqual(len(result), 2)

        # first file has no errors
        self.assertEqual(len(result[0][1]), 0)

        # second file has 10 errors
        self.assertEqual(len(result[1][1]), 10)
        errors = {}
        for report in result[1][1]:
            errors[report.idmsg] = errors.get(report.idmsg, 0) + 1
        self.assertEqual(errors['lines'], 2)
        self.assertEqual(errors['punct'], 2)
        self.assertEqual(errors['whitespace'], 4)
        self.assertEqual(errors['whitespace_eol'], 2)

    def test_checks_fuzzy(self):
        """Test checks on a gettext file including fuzzy strings."""
        po_check = PoCheck()
        po_check.set_check('fuzzy', True)
        result = po_check.check_files([local_path('fr_errors.po')])

        # be sure we have one file in result
        self.assertEqual(len(result), 1)

        # the file has 11 errors (with the fuzzy string)
        self.assertEqual(len(result[0][1]), 11)

    def test_replace_formatters_c(self):
        """Test removal of formatters in a C string."""
        self.assertEqual(replace_formatters('%s', 'c'), '')
        self.assertEqual(replace_formatters('%%', 'c'), '%')
        self.assertEqual(replace_formatters('%.02f', 'c'), '')
        self.assertEqual(replace_formatters('%!%s%!', 'c'), '%!%!')
        self.assertEqual(replace_formatters('%.02!', 'c'), '%.02!')
        self.assertEqual(
            replace_formatters('%.3fThis is a %stest', 'c'),
            'This is a test')
        self.assertEqual(
            replace_formatters('%.3fTest%s%d%%%.03f%luhere% s', 'c'),
            'Test%here')

    def test_replace_formatters_python(self):
        """Test removal of formatters in a python string."""
        # str.__mod__()
        self.assertEqual(replace_formatters('%s', 'python'), '')
        self.assertEqual(replace_formatters('%b', 'python'), '')
        self.assertEqual(replace_formatters('%%', 'python'), '%')
        self.assertEqual(replace_formatters('%.02f', 'python'), '')
        self.assertEqual(replace_formatters('%(sth)s', 'python'), 'sth')
        self.assertEqual(replace_formatters('%(sth)02f', 'python'), 'sth')
        # str.format()
        conditions = [
            (
                'First, thou shalt count to {0}', 'First, thou shalt count to ',
                'References first positional argument'),
            (
                'Bring me a {}', 'Bring me a ',
                'Implicitly references the first positional argument'),
            ('From {} to {}', 'From  to ', 'Same as "From {0} to {1}"'),
            (
                'My quest is {name}', 'My quest is ',
                'References keyword argument \'name\''),
            (
                'Weight in tons {0.weight}', 'Weight in tons ',
                '\'weight\' attribute of first positional arg'),
            (
                'Units destroyed: {players[0]}', 'Units destroyed: ',
                'First element of keyword argument \'players\'.'),
        ]
        for condition in conditions:
            self.assertEqual(
                replace_formatters(condition[0], 'python'),
                condition[1],
                condition[2],
            )

    def test_spelling_id(self):
        """Test spelling on source messages (English) of gettext files."""
        po_check = PoCheck()
        po_check.set_spelling_options('id', None, local_path('pwl.txt'))
        result = po_check.check_files([local_path('fr_spelling_id.po')])

        # be sure we have 1 file in result
        self.assertEqual(len(result), 1)

        # the file has 2 spelling errors: "Thsi" and "errro"
        errors = result[0][1]
        self.assertEqual(len(errors), 2)
        for i, word in enumerate(('Thsi', 'errro')):
            self.assertEqual(errors[i].idmsg, 'spelling-id')
            self.assertTrue(isinstance(errors[i].message, list))
            self.assertEqual(len(errors[i].message), 1)
            self.assertEqual(errors[i].message[0], word)

    def test_spelling_str(self):
        """Test spelling on translated messages of gettext files."""
        po_check = PoCheck()
        po_check.set_spelling_options('str', None, local_path('pwl.txt'))
        result = po_check.check_files([local_path('fr_spelling_str.po'),
                                       local_path('fr_language.po')])

        # be sure we have 2 files in result
        self.assertEqual(len(result), 2)

        # first file has 3 spelling errors: "CecX", "aabbcc" and "xxyyzz"
        errors = result[0][1]
        self.assertEqual(len(errors), 3)
        for i, word in enumerate(('CecX', 'aabbcc', 'xxyyzz')):
            self.assertEqual(errors[i].idmsg, 'spelling-str')
            self.assertTrue(isinstance(errors[i].message, list))
            self.assertEqual(len(errors[i].message), 1)
            self.assertEqual(errors[i].message[0], word)

        # second file has 1 error: dict/language "xyz" not found
        errors = result[1][1]
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].idmsg, 'dict')

    def test_spelling_bad_dict(self):
        """Test spelling with a bad dict option."""
        po_check = PoCheck()
        po_check.set_spelling_options('str', 'xxx', None)
        self.assertEqual(len(po_check.extra_checkers), 0)

    def test_spelling_bad_pwl(self):
        """Test spelling with a bad pwl option."""
        po_check = PoCheck()
        try:
            po_check.set_spelling_options('str', None,
                                          local_path('pwl_does_not_exist.txt'))
        except IOError:
            pass  # this exception is expected
        else:
            self.fail('No problem when using a non-existing pwl file!')


if __name__ == "__main__":
    unittest.main()
