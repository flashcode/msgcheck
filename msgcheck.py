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

enchant_found = False

import argparse
import os
import re
import shlex
import sys
import subprocess

# enchant module is optional, spelling is checked on demand
try:
    import enchant
    from enchant.checker import SpellChecker
    enchant_found = True
except:
    pass

NAME = 'msgcheck.py'
VERSION = '1.9'
AUTHOR = 'Sebastien Helleu <flashcode@flashtux.org>'


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

    def count_lines(self, s):
        """Count number of lines in a string or translation."""
        count = len(s.split('\n'))
        if count > 1 and s.endswith('\n'):
            count -= 1
        return count

    def error(self, message, mid, mstr):
        """Display an error found in gettext file (on stderr)."""
        print('=' * 70)
        if type(message) is not list:
            message = [message]
        for msg in message:
            print('%s:%d: %s%s' % (self.filename, self.line, '(fuzzy) ' if self.fuzzy else '', msg))
        if mid:
            print('---')
            for line in mid.split('\n'):
                print('%s' % line)
        print('---')
        for line in mstr.split('\n'):
            print('%s' % line)

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

    def check_whitespace(self, quiet):
        """Check whitespace at beginning and end of string. Return the number of errors detected."""
        errors = 0
        for mid, mstr in self.messages:
            if not mid or not mstr:
                continue
            # check whitespace at beginning of string
            if self.count_lines(mid) == 1:
                startin = len(mid) - len(mid.lstrip(' '))
                startout = len(mstr) - len(mstr.lstrip(' '))
                if startin != startout:
                    if not quiet:
                        self.error('whitespace at beginning: %d in string, %d in translation' % (startin, startout), mid, mstr)
                    errors += 1
            # check whitespace at end of string
            endin = len(mid) - len(mid.rstrip(' '))
            endout = len(mstr) - len(mstr.rstrip(' '))
            if endin != endout:
                if not quiet:
                    self.error('whitespace at end: %d in string, %d in translation' % (endin, endout), mid, mstr)
                errors += 1
        return errors

    def check_spelling(self, quiet, checkers, onlymisspelled):
        """Check spelling. Return the number of errors detected."""
        if not checkers:
            return 0
        errors = 0
        for mid, mstr in self.messages:
            if not mid or not mstr:
                continue
            # check spelling
            checkers[0].set_text(mstr)
            misspelled = []
            for err in checkers[0]:
                wrong = True
                for d in checkers[1:]:
                    if d.check(err.word):
                        wrong = False
                        break
                if wrong:
                    misspelled.append(err.word)
            if misspelled:
                if not quiet:
                    if onlymisspelled:
                        print('\n'.join(misspelled))
                    else:
                        self.error(['spelling: "%s"' % word for word in misspelled], None, mstr)
                errors += len(misspelled)
        return errors


class PoFile:

    def __init__(self, filename, args):
        self.filename = os.path.abspath(filename)
        self.args = args
        self.props = {'language': '', 'charset': 'utf-8'}
        self.msgs = []
        self.checkers = []

    def add_message(self, filename, numline_msgid, msgfuzzy, msg):
        """Add a message from PO file in list of messages."""
        if 'msgid' in msg and len(msg['msgid']) == 0:
            # find file language/charset in properties (first string without msgid)
            m = re.search(r'language: ([a-zA-Z-_]+)', msg.get('msgstr', ''), re.IGNORECASE)
            if m:
                self.props['language'] = m.group(1)
                if self.args.spelling:
                    try:
                        d = enchant.DictWithPWL(self.props['language'], args.pwl[0] if args.pwl else None)
                        self.checkers.append(SpellChecker(d))
                    except:
                        print('%s:%d: enchant dictionary not found for language "%s"'
                              % (self.filename, numline_msgid, self.props['language']))
                        self.checkers = []
                    if self.args.dicts:
                        for lang in self.args.dicts[0].split(','):
                            try:
                                d = enchant.Dict(lang)
                                self.checkers.append(SpellChecker(d))
                            except:
                                print('%s: enchant dictionary not found for language "%s"'
                                      % (self.filename, lang))
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
                        fuzzy = 'fuzzy' in line
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

    def display_translations(self):
        """Display all translations."""
        for msg in self.msgs:
            if msg.fuzzy and not self.args.fuzzy:
                continue
            for mid, mstr in msg.messages:
                if mid and mstr:
                    print('%s\n---' % mstr)

    def check(self):
        """Check translations in PO file. Return the number of errors detected."""
        if not self.msgs:
            return 0
        errors = 0
        for msg in self.msgs:
            if msg.fuzzy and not self.args.fuzzy:
                continue
            if self.args.lines:
                errors += msg.check_lines_number(self.args.quiet)
            if self.args.punct:
                errors += msg.check_punctuation(self.args.quiet)
            if self.args.whitespace:
                errors += msg.check_whitespace(self.args.quiet)
            if self.args.spelling:
                errors += msg.check_spelling(self.args.quiet, self.checkers, self.args.onlymisspelled)
        return errors

# parse command line arguments
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description='''
%s %s (C) 2009-2013 %s

Perform some checks on gettext files.
''' % (NAME, VERSION, AUTHOR),
                                 epilog='''
Environment variable 'MSGCHECK_OPTIONS' can be set with some default options.

Return value:
  0: all files checked are OK (0 errors) (or --extract given)
  n: number of files with errors (n >= 1)
''')
parser.add_argument('-c', '--compile', action='store_false',
                    help='do not check compilation of file (with `msgfmt -c`)')
parser.add_argument('-f', '--fuzzy', action='store_true',
                    help='check fuzzy strings (default: ignored)')
parser.add_argument('-l', '--lines', action='store_false',
                    help='do not check number of lines')
parser.add_argument('-p', '--punct', action='store_false',
                    help='do not check punctuation at end of string')
parser.add_argument('-s', '--spelling', action='store_true',
                    help='check spelling')
parser.add_argument('-d', '--dicts', nargs=1,
                    help='comma-separated list of extra dictionaries to use (in addition to file language)')
parser.add_argument('--pwl', nargs=1,
                    help='file with personal word list used when checking spelling')
parser.add_argument('-m', '--onlymisspelled', action='store_true',
                    help='display only misspelled words (no error, line number and translation)')
parser.add_argument('-w', '--whitespace', action='store_false',
                    help='do not check whitespace at beginning/end of string')
parser.add_argument('--extract', action='store_true',
                    help='display all translations and exit (all checks except compilation are disabled in this mode)')
parser.add_argument('-q', '--quiet', action='store_true',
                    help='quiet mode: only display number of errors')
parser.add_argument('-v', '--version', action='version', version=VERSION)
parser.add_argument('file', nargs='+', help='gettext file(s) to check (*.po files)')
if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
args = parser.parse_args(shlex.split(os.getenv('MSGCHECK_OPTIONS') or '') + sys.argv[1:])

# exit now with error if spelling was asked but python enchant module was not found
if args.spelling and not enchant_found:
    print('Error: "enchant" module was not found to check spelling')
    print('Please install python-enchant.')
    sys.exit(1)

# check files
errors_total = 0
files_with_errors = 0
messages = []
for filename in args.file:
    errors = 0
    po = PoFile(filename, args)
    if not args.compile or po.compile() == 0:
        po.read()
        if args.extract:
            po.display_translations()
        else:
            errors = po.check()
            if errors == 0:
                messages.append('%s: OK' % po.filename)
            else:
                messages.append('%s: %d errors (%s)' % (po.filename, errors,
                                                        'almost good!' if errors <= 10 else 'uh oh... try again!'))
    else:
        print('%s: compilation FAILED' % po.filename)
        errors = 1
    if errors > 0:
        files_with_errors += 1
    errors_total += errors

# exit now if we extracted translations or if we displayed only misspelled words
if args.extract or args.onlymisspelled:
    sys.exit(0)

# display files with number of errors
if errors > 0 and not args.quiet:
    print('=' * 70)
for msg in messages:
    print(msg)

# display total (if many files processed)
if len(args.file) > 1:
    print('---')
    if errors_total == 0:
        print('TOTAL: all OK')
    else:
        print('TOTAL: %d files OK, %d files with %d errors' % (len(args.file) - files_with_errors,
                                                               files_with_errors, errors_total))

# exit
sys.exit(files_with_errors)
