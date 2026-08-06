# SPDX-FileCopyrightText: 2009-2026 Sébastien Helleu <flashcode@flashtux.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Gettext file checker."""

from msgcheck.msgcheck import check


def main() -> None:
    """Check files."""
    check()
