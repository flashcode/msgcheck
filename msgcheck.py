#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009-2013 Sebastien Helleu <flashcode@flashtux.org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

#
# Perform some checks on gettext files:
# - check compilation (msgfmt -c)
# - for each translation which is not fuzzy/empty:
#    - check number of lines in translated string
#    - check spaces at beginning/end of string
#    - check punctuation at end of string
#
# Syntax:
#    msgcheck.py [-n] [-s] [-p] file.po [file.po...]
#
# 2013-06-29, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.7: add options to disable some checks
# 2013-06-29, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.6: check punctuation at end of string
# 2013-01-02, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.5: replace os.system by subprocess, display syntax when script
#                  is called without filename, rename script to "msgcheck.py"
# 2012-09-21, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.4: add check of compilation with "msgfmt -c"
# 2011-04-14, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.3: allow multiple po filenames
# 2011-04-10, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.2: add check of spaces at beginning/end of strings
# 2010-03-22, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.1: initial release
#

import os, sys, subprocess

def error(msg_error, msg_in):
    """Display an error found in gettext file."""
    print('%s\nERROR: %s:\n\n%s\n' % ('='*60, msg_error, msg_in))

if len(sys.argv) >= 2:
    # if user gives .po filename, then run checks on file:
    # 1. check compilation (msgfmt -c)
    # 2. remove untranslated/fuzzy strings, and call msgexec, with this script
    #    as argument: this script will be called for each string in file
    options = ''
    for option in sys.argv[1:]:
        if option[0] == '-':
            options += option[1:]
    os.putenv('MSGCHECK_OPTIONS', options)
    for filename in sys.argv[1:]:
        if filename[0] != '-':
            # check compilation
            print('Checking compilation of %s...' % filename)
            subprocess.call(['msgfmt', '-c', '-o', '/dev/null', filename])
            # check each translation in file
            print('Checking lines in %s...' % filename)
            p1 = subprocess.Popen(['msgattrib', '--translated', '--no-fuzzy', filename], stdout=subprocess.PIPE)
            p2 = subprocess.Popen(['msgexec', sys.argv[0]], stdin=p1.stdout)
            p1.stdout.close()
            p2.communicate()[0]
else:
    # this is an automatic call from 'msgexec' command:
    # read original string from environment variable 'MSGEXEC_MSGID'
    msg_in = os.getenv('MSGEXEC_MSGID')

    # no message found, display syntax and exit
    if msg_in is None:
        name = os.path.basename(sys.argv[0])
        print('')
        print('Syntax:  %s [options] file.po [file.po...]' % name)
        print('')
        print('Options:')
        print('  -n  do not check number of lines')
        print('  -s  do not check spaces at beginning/end of string')
        print('  -p  do not check punctuation at end of string')
        print('')
        print('Examples:')
        print('  %s fr.po' % name)
        print('  %s -p ja.po' % name)
        sys.exit(0)

    # options for checks
    options = os.getenv('MSGCHECK_OPTIONS')

    # count number of lines in message
    nb_in = len(msg_in.split('\n'))

    # read translated string (given in standard input)
    list_msg_out = sys.stdin.readlines()
    nb_out = len(list_msg_out)
    msg_out = '\n'.join(list_msg_out)

    if not 'n' in options:
        # check number of lines
        if msg_in.endswith('\n'):
            nb_in = nb_in - 1
        if msg_in != '' and nb_in != nb_out:
            error('number of lines: %d in string, %d in translation' % (nb_in, nb_out), msg_in)

    if not 's' in options:
        # check spaces at beginning of string
        if nb_in == 1:
            startin = len(msg_in) - len(msg_in.lstrip(' '))
            startout = len(msg_out) - len(msg_out.lstrip(' '))
            if startin != startout:
                error('spaces at beginning: %d in string, %d in translation' % (startin, startout), msg_in)

        # check spaces at end of string
        endin = len(msg_in) - len(msg_in.rstrip(' '))
        endout = len(msg_out) - len(msg_out.rstrip(' '))
        if endin != endout:
            error('spaces at end: %d in string, %d in translation' % (endin, endout), msg_in)

    if not 'p' in options:
        # check punctuation at end of string
        for punct in (':', ';', ',', '.', '...'):
            length = len(punct)
            if len(msg_in) >= length and len(msg_out) >= length \
                    and msg_in.endswith(punct) and not msg_out.endswith(punct):
                error('end punctuation: "%s" in string, not in translation' % punct, msg_in)
