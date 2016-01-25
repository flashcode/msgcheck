# -*- coding: utf-8 -*-
#
# Copyright (C) 2009-2016 Sébastien Helleu <flashcode@flashtux.org>
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
Some utility functions for msgcheck.
"""

from __future__ import print_function


# TODO: add support for other languages
STR_FORMATTERS = {
    'c': ('\\', '%', '#- +\'I.0123456789hlLqjzt', 'diouxXeEfFgGaAcsCSpnm'),
}


def count_lines(string):
    """Count the number of lines in a string or translation."""
    count = len(string.split('\n'))
    if count > 1 and string.endswith('\n'):
        count -= 1
    return count


# pylint: disable=too-many-branches
def replace_formatters(string, replace, fmt):
    """
    Replace formatters (like "%s" or "%03d") with a replacement string.
    """
    if fmt not in STR_FORMATTERS:
        return string
    formatters = STR_FORMATTERS[fmt]
    formatter, escape = (False, False)
    strformat = []
    result = []

    for char in string:
        if formatter:
            if char == formatters[1]:
                result.append(char)
                formatter = False
            elif char in formatters[2]:
                strformat.append(char)
            elif char in formatters[3]:
                result.append(replace)
                formatter = False
            else:
                strformat.append(char)
                result += strformat
                formatter = False
        elif escape:
            result.append(formatters[0])
            result.append(char)
            escape = False
        elif char == formatters[0]:
            escape = True
        elif char == formatters[1]:
            formatter = True
            strformat = [char]
        else:
            result.append(char)

    if escape:  # unterminated escaped char?
        result.append(formatters[0])
    elif formatter:  # unterminated formatter?
        result.append(replace)

    return ''.join(result)
