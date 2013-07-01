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
# Perform some checks on gettext files (see README.md for more info).
#

import os, re, sys, subprocess

NAME='msgcheck.py'
VERSION='1.0'

class PoMessage:

    def __init__(self, filename, fileprops, line, fuzzy, msg):
        self.filename = filename
        self.fileprops = fileprops
        self.line = line
        self.fuzzy = fuzzy
        # interpret special chars like "\n" in messages
        if sys.version_info >= (3,):
            # python 3.x
            for m in msg:
                msg[m] = str(bytes(msg[m], self.fileprops['charset']).decode('unicode_escape').encode('latin1'), self.fileprops['charset'])
        else:
            # python 2.x
            for m in msg:
                msg[m] = msg[m].decode('string_escape')
        # build messages, which a list of tuple (string, translation)
        self.messages = []
        if 'msgid_plural' in msg:
            i = 0
            while True:
                key = 'msgstr[%d]' % i
                if key not in msg:
                    break
                self.messages.append((msg['msgid_plural'], msg[key]))
                i += 1
        else:
            self.messages.append((msg.get('msgid', ''), msg.get('msgstr', '')))
        self.utf8 = re.search(r'utf-?8', os.getenv('LANG').lower())

    def count_lines(self, s):
        """Count number of lines in a string or translation."""
        count = len(s.split('\n'))
        if count > 1 and s.endswith('\n'):
            count -= 1
        return count

    def error(self, message, mid, mstr):
        """Display an error found in gettext file (on stderr)."""
        if self.utf8:
            bar = { '|=': '╒', '|-': '├', '|_': '└', '-': '─', '=': '═', '|': '│' }  # modern
        else:
            bar = { '|=': '=', '|-': '-', '|_': '-', '-': '-', '=': '=', '|': '' }   # old school
        print('%s%s' % (bar['|='], bar['=']*24))
        print('%s%s: line %d%s: %s:' % (bar['|'], self.filename, self.line, ' (fuzzy)' if self.fuzzy else '', message))
        print('%s%s' % (bar['|-'], bar['-']*3))
        for line in mid.split('\n'):
            print('%s%s' % (bar['|'], line))
        print('%s%s' % (bar['|-'], bar['-']*3))
        for line in mstr.split('\n'):
            print('%s%s' % (bar['|'], line))
        print('%s%s' % (bar['|_'], bar['-']*8))

    def check_lines_number(self, quiet):
        """Check number of lines in string and translation. Return the number of errors detected."""
        errors = 0
        for mid, mstr in self.messages:
            if not mid or not mstr:
                continue
            nb_id = self.count_lines(mid)
            nb_str = self.count_lines(mstr)
            if nb_id != nb_str:
                if not quiet:
                    self.error('number of lines: %d in string, %d in translation' % (nb_id, nb_str), mid, mstr)
                errors += 1
        return errors

    def check_spaces(self, quiet):
        """Check spaces at beginning and end of string. Return the number of errors detected."""
        errors = 0
        for mid, mstr in self.messages:
            if not mid or not mstr:
                continue
            # check spaces at beginning of string
            if self.count_lines(mid) == 1:
                startin = len(mid) - len(mid.lstrip(' '))
                startout = len(mstr) - len(mstr.lstrip(' '))
                if startin != startout:
                    if not quiet:
                        self.error('spaces at beginning: %d in string, %d in translation' % (startin, startout), mid, mstr)
                    errors += 1
            # check spaces at end of string
            endin = len(mid) - len(mid.rstrip(' '))
            endout = len(mstr) - len(mstr.rstrip(' '))
            if endin != endout:
                if not quiet:
                    self.error('spaces at end: %d in string, %d in translation' % (endin, endout), mid, mstr)
                errors += 1
        return errors

    def check_punctuation(self, quiet):
        """Check punctuation at end of string. Return the number of errors detected."""
        errors = 0
        for mid, mstr in self.messages:
            if not mid or not mstr:
                continue
            puncts = [(':', ':'), (';', ';'), (',', ','), ('...', '...')]
            # special symbols in some languages
            if self.fileprops['language'].startswith('ja'):
                puncts.append(('.', '。'))
            else:
                puncts.append(('.', '.'))
            for punctid, punctstr in puncts:
                len_pid = len(punctid)
                len_pstr = len(punctstr)
                if len(mid) >= len_pid and len(mstr) >= len_pstr:
                    match_id = mid.endswith(punctid)
                    match_str = mstr.endswith(punctstr)
                    if match_id and match_str:
                        break
                    if match_id and not match_str:
                        if not quiet:
                            self.error('end punctuation: "%s" in string, "%s" not in translation' % (punctid, punctstr), mid, mstr)
                        errors += 1
                        break
                    if not match_id and match_str:
                        if not quiet:
                            self.error('end punctuation: "%s" in translation, "%s" not in string' % (punctstr, punctid), mid, mstr)
                        errors += 1
                        break
        return errors

class PoFile:

    def __init__(self, filename):
        self.filename = filename
        self.props = { 'language': '', 'charset': 'utf-8' }
        self.msgs = []

    def add_message(self, filename, numline_msgid, msgfuzzy, msg):
        """Add a message from PO file in list of messages."""
        if 'msgid' in msg and len(msg['msgid']) == 0:
            # find file language/charset in properties (first string without msgid)
            m = re.search(r'language: ([a-zA-Z-_]+)', msg.get('msgstr', ''), re.IGNORECASE)
            if m:
                self.props['language'] = m.group(1)
            m = re.search(r'charset=([a-zA-Z0-9-_]+)', msg.get('msgstr', ''), re.IGNORECASE)
            if m:
                self.props['charset'] = m.group(1)
        self.msgs.append(PoMessage(filename, self.props, numline_msgid, msgfuzzy, msg))

    def read(self):
        """Read messages in PO file."""
        self.msgs = []
        (numline, numline_msgid) = (0, 0)
        (fuzzy, msgfuzzy) = (False, False)
        msg = {}
        msgcurrent = ''
        try:
            with open(self.filename, 'r') as f:
                for line in f.readlines():
                    numline += 1
                    line = line.strip()
                    if len(line) == 0:
                        continue
                    if line[0] == '#':
                        if line.startswith('#, fuzzy'):
                            fuzzy = True
                        continue
                    if line.startswith('msg'):
                        m = re.match(r'([a-zA-Z0-9-_]+(\[\d+\])?)[ \t](.*)', line)
                        if m:
                            oldmsgcurrent = msgcurrent
                            msgcurrent = m.group(1)
                            line = m.group(3)
                            if msgcurrent == 'msgid':
                                if oldmsgcurrent.startswith('msgstr'):
                                    self.add_message(self.filename, numline_msgid, msgfuzzy, msg)
                                msgfuzzy = fuzzy
                                fuzzy = False
                                msg = {}
                                numline_msgid = numline
                    if msgcurrent and line.startswith('"'):
                        msg[msgcurrent] = msg.get(msgcurrent, '') + line[1:-1]
                if msgcurrent == 'msgstr':
                    self.add_message(self.filename, numline_msgid, msgfuzzy, msg)
        except Exception as e:
            print('Error reading file %s, line %d:' % (self.filename, numline))
            print(e)
            self.msgs = []

    def compile(self):
        """Compile PO file and return the return code."""
        return subprocess.call(['msgfmt', '-c', '-o', '/dev/null', self.filename])

    def check(self, options):
        """Check translations in PO file. Return the number of errors detected."""
        if not self.msgs:
            return 0
        errors = 0
        quiet = 'q' in options
        for msg in self.msgs:
            if msg.fuzzy and 'f' not in options:
                continue
            if 'n' not in options:
                errors += msg.check_lines_number(quiet)
            if 's' not in options:
                errors += msg.check_spaces(quiet)
            if 'p' not in options:
                errors += msg.check_punctuation(quiet)
        return errors

# display help if no file given
if len(sys.argv) < 2:
    print('''
%s %s (C) 2009-2013 Sebastien Helleu <flashcode@flashtux.org>

Syntax:
  %s [options] file.po [file.po...]

Options:
  -f  check fuzzy strings (fuzzy are ignored by default)
  -c  do not check compilation of file (with `msgfmt -c`)
  -n  do not check number of lines
  -s  do not check spaces at beginning/end of string
  -p  do not check punctuation at end of string
  -q  quiet mode: only display number of errors
  -v  display version

Notes: 1. Options apply to all files given *after* the option.
       2. Options can be reversed with "+" prefix, for example +p will check punctuation.

Return value:
  0: all files checked are OK (0 errors)
  n: number of files with errors (n >= 1)

Examples:
  %s fr.po
  %s fr.po -p ja.po
''' % (NAME, VERSION, NAME, NAME, NAME))
    sys.exit(0)

# process options and files
options = []
errors_total = 0
files = 0
files_with_errors = 0
messages = []
for opt in sys.argv[1:]:
    if opt == '-v':
        print('%s' % VERSION)
        sys.exit(0)
    elif opt[0] == '-':
        for o in opt[1:]:
            if o not in options:
                options.append(o)
    elif opt[0] == '+':
        for o in opt[1:]:
            if o in options:
                options.remove(o)
    else:
        files += 1
        errors = 0
        po = PoFile(opt)
        if 'c' in options or po.compile() == 0:
            po.read()
            errors = po.check(options)
            if errors == 0:
                messages.append('%s: OK' % opt)
            else:
                messages.append('%s: %d errors (%s)' % (opt, errors,
                                                        'almost good!' if errors <= 10 else 'uh oh... try again!'))
        else:
            print('%s: compilation FAILED' % opt)
            errors = 1
        if errors > 0:
            files_with_errors += 1
        errors_total += errors

# display files with number of errors
for msg in messages:
    print(msg)

# display total (if many files processed)
if files > 1:
    print('---')
    if errors_total == 0:
        print('TOTAL: all OK')
    else:
        print('TOTAL: %d files OK, %d files with %d errors' % (files - files_with_errors,
                                                               files_with_errors, errors_total))

# exit
sys.exit(files_with_errors)
