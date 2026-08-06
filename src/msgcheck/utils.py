# SPDX-FileCopyrightText: 2009-2026 Sébastien Helleu <flashcode@flashtux.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

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
