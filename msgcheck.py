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

from __future__ import print_function

import argparse
from codecs import escape_decode
import os
import re
import shlex
import sys
import subprocess
import traceback

# enchant module is optional, spelling is checked on demand
# (argument -s/--spell)
enchant_found = False
try:
    import enchant
    from enchant.checker import SpellChecker
    enchant_found = True
except:
    pass

VERSION = '2.2'


class PoMessage:
    """
    A message from a gettext file. It is stored as a list of tuples
    (string, translation).
    The list usually have one element, except if the plural form is
    used.

    Example of a single string (french translation):

        msgid "Hello"
        msgstr "Bonjour"

        ==>  [('Hello', 'Bonjour')]

    Example with a plural form (french translations):

        #, c-format
        msgid "%d file found"
        msgid_plural "%d files found"
        msgstr[0] "%d fichier trouvé"
        msgstr[1] "%d fichiers trouvés"

        ==>  [('%d files found', '%d fichier trouvé'),
              ('%d files found', '%d fichiers trouvés')]
    """

    def __init__(self, msg, charset, fuzzy, line):
        """Build a PO message."""
        # unescape strings
        if sys.version_info < (3,):
            # python 2.x
            msg = {k: escape_decode(v)[0] for k, v in msg.items()}
        else:
            # python 3.x
            msg = {k: escape_decode(v)[0]. decode(charset)
                   for k, v in msg.items()}
        # build messages as a list of tuples: (string, translation)
        self.messages = []
        if 'msgid_plural' in msg:
            i = 0
            while True:
                key = 'msgstr[{0}]'.format(i)
                if key not in msg:
                    break
                self.messages.append((msg['msgid_plural'], msg[key]))
                i += 1
        else:
            self.messages.append((msg.get('msgid', ''), msg.get('msgstr', '')))
        self.fuzzy = fuzzy
        self.line = line


class PoFile:
    """
    A gettext file. It includes functions to read the file, and perform
    checks on the translations.
    """

    def __init__(self, filename, args):
        self.filename = os.path.abspath(filename)
        self.args = args
        self.props = {'language': '', 'charset': 'utf-8'}
        self.msgs = []
        self.checkers = []

    def add_message(self, filename, numline_msgid, msgfuzzy, msg):
        """
        Add a message from PO file in list of messages.
        """
        if 'msgid' in msg and len(msg['msgid']) == 0:
            # find file language/charset in properties
            # (first string without msgid)
            m = re.search(r'language: ([a-zA-Z-_]+)', msg.get('msgstr', ''),
                          re.IGNORECASE)
            if m:
                self.props['language'] = m.group(1)
                if self.args.spelling:
                    try:
                        d = enchant.DictWithPWL(self.props['language'],
                                                args.pwl)
                        self.checkers.append(SpellChecker(d))
                    except:
                        print(self.filename, ':', numline_msgid,
                              ': enchant dictionary not found for language ',
                              self.props['language'],
                              sep='')
                        self.checkers = []
                    if self.args.dicts:
                        for lang in self.args.dicts.split(','):
                            try:
                                d = enchant.Dict(lang)
                                self.checkers.append(SpellChecker(d))
                            except:
                                print(self.filename,
                                      ': enchant dictionary not found for '
                                      'language ',
                                      lang,
                                      sep='')
            m = re.search(r'charset=([a-zA-Z0-9-_]+)', msg.get('msgstr', ''),
                          re.IGNORECASE)
            if m:
                self.props['charset'] = m.group(1)
        self.msgs.append(PoMessage(msg, self.props['charset'], msgfuzzy,
                                   numline_msgid,))

    def read(self):
        """
        Read messages in PO file.
        """
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
                        m = re.match(r'([a-zA-Z0-9-_]+(\[\d+\])?)[ \t](.*)',
                                     line)
                        if m:
                            oldmsgcurrent = msgcurrent
                            msgcurrent = m.group(1)
                            line = m.group(3)
                            if msgcurrent == 'msgid':
                                if oldmsgcurrent.startswith('msgstr'):
                                    self.add_message(self.filename,
                                                     numline_msgid,
                                                     msgfuzzy,
                                                     msg)
                                msgfuzzy = fuzzy
                                fuzzy = False
                                msg = {}
                                numline_msgid = numline
                    if msgcurrent and line.startswith('"'):
                        msg[msgcurrent] = msg.get(msgcurrent, '') + line[1:-1]
                if msgcurrent.startswith('msgstr'):
                    self.add_message(self.filename,
                                     numline_msgid,
                                     msgfuzzy,
                                     msg)
        except Exception:
            traceback.print_exc()
            print('Error reading file ', self.filename, ', line ', numline,
                  sep='')
            self.msgs = []

    def compile(self):
        """
        Compile PO file (with msgfmt -c).
        Return the return code.
        """
        return subprocess.call(['msgfmt', '-c', '-o', '/dev/null',
                                self.filename])

    def display_translations(self):
        """
        Display all translations.
        """
        for msg in self.msgs:
            if msg.fuzzy and not self.args.fuzzy:
                continue
            for mid, mstr in msg.messages:
                if mid and mstr:
                    print(mstr, '---', sep='\n')

    def error(self, msg, mid, mstr, error_msg):
        """
        Display an error found in gettext file (on stderr).
        """
        if self.args.quiet:
            return
        print('=' * 70)
        if type(error_msg) is not list:
            error_msg = [error_msg]
        for err in error_msg:
            print(self.filename, ':', msg.line, ': ',
                  '(fuzzy) ' if msg.fuzzy else '',
                  err, sep='')
        if mid:
            print('---', mid, sep='\n')
        print('---', mstr, sep='\n')

    def count_lines(self, s):
        """
        Count number of lines in a string or translation.
        """
        count = len(s.split('\n'))
        if count > 1 and s.endswith('\n'):
            count -= 1
        return count

    def check_lines_number(self, msg):
        """
        Check number of lines in string and translation.
        Return the number of errors detected.
        """
        errors = 0
        for mid, mstr in msg.messages:
            if not mid or not mstr:
                continue
            nb_id = self.count_lines(mid)
            nb_str = self.count_lines(mstr)
            if nb_id != nb_str:
                self.error(msg, mid, mstr,
                           'number of lines: {0} in string, '
                           '{1} in translation'.format(nb_id, nb_str))
                errors += 1
        return errors

    def check_punctuation(self, msg):
        """
        Check punctuation at end of string.
        Return the number of errors detected.
        """
        errors = 0
        for mid, mstr in msg.messages:
            if not mid or not mstr:
                continue
            puncts = [(':', ':'), (';', ';'), (',', ','), ('...', '...')]
            # special symbols in some languages
            if self.props['language'].startswith('ja'):
                puncts.append(('.', '。'))
            else:
                puncts.append(('.', '.'))
            for punctid, punctstr in puncts:
                len_pid = len(punctid)
                len_pstr = len(punctstr)
                if len(mid) < len_pid or len(mstr) < len_pstr:
                    continue
                match_id = mid.endswith(punctid)
                match_str = mstr.endswith(punctstr)
                if match_id and match_str:
                    break
                if match_id and not match_str:
                    self.error(msg, mid, mstr,
                               'end punctuation: "{0}" in string, '
                               '"{1}" not in translation'.format(punctid,
                                                                 punctstr))
                    errors += 1
                    break
                if not match_id and match_str:
                    self.error(msg, mid, mstr,
                               'end punctuation: "{0}" in translation, '
                               '"{1}" not in string'.format(punctstr, punctid))
                    errors += 1
                    break
        return errors

    def check_whitespace(self, msg):
        """
        Check whitespace at beginning and end of string.
        Return the number of errors detected.
        """
        errors = 0
        for mid, mstr in msg.messages:
            if not mid or not mstr:
                continue
            # check whitespace at beginning of string
            if self.count_lines(mid) == 1:
                startin = len(mid) - len(mid.lstrip(' '))
                startout = len(mstr) - len(mstr.lstrip(' '))
                if startin != startout:
                    self.error(msg, mid, mstr,
                               'whitespace at beginning: {0} in string, '
                               '{1} in translation'.format(startin, startout))
                    errors += 1
            # check whitespace at end of string
            endin = len(mid) - len(mid.rstrip(' '))
            endout = len(mstr) - len(mstr.rstrip(' '))
            if endin != endout:
                self.error(msg, mid, mstr,
                           'whitespace at end: {0} in string, '
                           '{1} in translation'.format(endin, endout))
                errors += 1
        return errors

    def check_spelling(self, msg):
        """
        Check spelling.
        Return the number of errors detected.
        """
        if not self.checkers:
            return 0
        errors = 0
        for mid, mstr in msg.messages:
            if not mid or not mstr:
                continue
            # check spelling
            self.checkers[0].set_text(mstr)
            misspelled = []
            for err in self.checkers[0]:
                misspelled_word = True
                for d in self.checkers[1:]:
                    if d.check(err.word):
                        misspelled_word = False
                        break
                if misspelled_word:
                    misspelled.append(err.word)
            if misspelled:
                if self.args.only_misspelled:
                    print('\n'.join(misspelled))
                else:
                    self.error(msg, None, mstr,
                               ['spelling: "{0}"'.format(word)
                                for word in misspelled])
                errors += len(misspelled)
        return errors

    def check(self):
        """
        Check translations in PO file.
        Return the number of errors detected.
        """
        if not self.msgs:
            return 0
        errors = 0
        for msg in self.msgs:
            if msg.fuzzy and not self.args.fuzzy:
                continue
            if not self.args.no_lines:
                errors += self.check_lines_number(msg)
            if not self.args.no_punct:
                errors += self.check_punctuation(msg)
            if not self.args.no_whitespace:
                errors += self.check_whitespace(msg)
            if self.args.spelling:
                errors += self.check_spelling(msg)
        return errors


def main():
    """Main function, entry point."""
    # parse command line arguments
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        fromfile_prefix_chars='@',
        description='Perform some checks on gettext files.',
        epilog='''
Environment variable "MSGCHECK_OPTIONS" can be set with default options.
Argument "@file.txt" can be used to read default options in a file.

The script returns:
  0: all files checked are OK (or --extract/--only-misspelled given)
  n: number of files with errors (n >= 1)
''')
    parser.add_argument('-c', '--no-compile', action='store_true',
                        help='do not check compilation of file')
    parser.add_argument('-f', '--fuzzy', action='store_true',
                        help='check fuzzy strings')
    parser.add_argument('-l', '--no-lines', action='store_true',
                        help='do not check number of lines')
    parser.add_argument('-p', '--no-punct', action='store_true',
                        help='do not check punctuation at end of strings')
    parser.add_argument('-s', '--spelling', action='store_true',
                        help='check spelling')
    parser.add_argument('-d', '--dicts',
                        help='comma-separated list of extra dictionaries '
                        'to use (in addition to file language)')
    parser.add_argument('-P', '--pwl',
                        help='file with personal word list used when checking '
                        'spelling')
    parser.add_argument('-m', '--only-misspelled', action='store_true',
                        help='display only misspelled words (no error, line '
                        'number and translation)')
    parser.add_argument('-w', '--no-whitespace', action='store_true',
                        help='do not check whitespace at beginning/end of '
                        'strings')
    parser.add_argument('-e', '--extract', action='store_true',
                        help='display all translations and exit '
                        '(all checks except compilation are disabled in this '
                        'mode)')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='quiet mode: only display number of errors')
    parser.add_argument('-v', '--version', action='version', version=VERSION)
    parser.add_argument('file', nargs='+',
                        help='gettext file(s) to check (*.po files)')
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    args = parser.parse_args(shlex.split(os.getenv('MSGCHECK_OPTIONS') or '') +
                             sys.argv[1:])

    # exit now with error if spelling was asked but python enchant module was
    # not found
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
        if args.no_compile or po.compile() == 0:
            po.read()
            if args.extract:
                po.display_translations()
            else:
                errors = po.check()
                if errors == 0:
                    messages.append('{0}: OK'.format(po.filename))
                else:
                    messages.append('{0}: {1} errors ({2})'
                                    ''.format(po.filename,
                                              errors,
                                              'almost good!' if errors <= 10
                                              else 'uh oh... try again!'))
        else:
            print(po.filename, ': compilation FAILED', sep='')
            errors = 1
        if errors > 0:
            files_with_errors += 1
        errors_total += errors

    # exit now if we extracted translations or if we displayed only misspelled
    # words
    if args.extract or args.only_misspelled:
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
            print('TOTAL: {0} files OK'.format(len(args.file)))
        else:
            print('TOTAL: {0} files OK, {1} files with {2} errors'
                  ''.format(len(args.file) - files_with_errors,
                            files_with_errors,
                            errors_total))

    # exit
    sys.exit(files_with_errors)


if __name__ == "__main__":
    main()
