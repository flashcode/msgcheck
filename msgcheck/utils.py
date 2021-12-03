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

"""Some utility functions for msgcheck."""

from __future__ import print_function

from collections import defaultdict
import re


# TODO: add support for other languages
STR_FORMATTERS = defaultdict(list)
STR_FORMATTERS.update({
    'c': (
        (r'[\%]{2}', '%'),
        (r'\%([ hlL\d\.\-\+\#\*]+)?[cdieEfgGosuxXpn]', r''),
    ),
    'python': (
        (r'[\%]{2}', '%'),
        (r'\%([.\d]+)?[bcdeEfFgGnosxX]', r''),
        (r'\%(\([^)]*\))([.\d]+)?[bcdeEfFgGnosxX]', r''),
    ),
    'python-brace': (
        (r'\{([^\:\}]*)?(:[^\}]*)?\}', r''),
    ),
})


def count_lines(string):
    """Count the number of lines in a string or translation."""
    count = len(string.split('\n'))
    if count > 1 and string.endswith('\n'):
        count -= 1
    return count


def replace_formatters(string, fmt):
    r"""
    Replace formatters (like "%s" or "%03d") with a replacement string.
    """
    for pattern, repl in STR_FORMATTERS[fmt]:
        string = re.sub(pattern, repl, string)
    return string
