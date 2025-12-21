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

"""Some utility functions for msgcheck."""

import re

STR_FORMATTERS = {
    "c": [
        (r"[\%]{2}", "%"),
        (r"\%([ hlL\d\.\-\+\#\*]+)?[cdieEfgGosuxXpn]", r""),
    ],
    "python": [
        (r"[\%]{2}", "%"),
        (r"\%([.\d]+)?[bcdeEfFgGnosxX]", r""),
        (r"\%(\([^)]*\))([.\d]+)?[bcdeEfFgGnosxX]", r""),
    ],
    "python-brace": [
        (r"\{([^\:\}]*)?(:[^\}]*)?\}", r""),
    ],
}


def count_lines(string: str) -> int:
    """Count the number of lines in a string or translation."""
    count = len(string.split("\n"))
    if count > 1 and string.endswith("\n"):
        count -= 1
    return count


def replace_formatters(string: str, fmt: str) -> str:
    r"""Replace formatters (like "%s" or "%03d") with a replacement string."""
    for pattern, repl in STR_FORMATTERS.get(fmt, []):
        string = re.sub(pattern, repl, string)
    return string
