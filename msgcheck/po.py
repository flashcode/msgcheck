# -*- coding: utf-8 -*-
#
# Copyright (C) 2009-2014 Sébastien Helleu <flashcode@flashtux.org>
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
Classes to read and check PO (gettext) files.
"""

from __future__ import print_function

from codecs import escape_decode
import os
import re
import subprocess
import sys

# enchant module is optional, spelling is checked on demand
# (argument -s/--spell)
ENCHANT_FOUND = False
try:
    from enchant import Dict, DictWithPWL, DictNotFoundError
    from enchant.checker import SpellChecker
    ENCHANT_FOUND = True
except ImportError:
    pass


def count_lines(string):
    """
    Count the number of lines in a string or translation.
    """
    count = len(string.split('\n'))
    if count > 1 and string.endswith('\n'):
        count -= 1
    return count


# pylint: disable=too-few-public-methods
class PoReport(object):
    """A message in report (commonly an error in detected in gettext file)."""

    # pylint: disable=too-many-arguments
    def __init__(self, message, idmsg='', filename='-', line=0, mid='',
                 mstr='', fuzzy=False):
        self.message = message
        self.idmsg = idmsg
        self.filename = filename
        self.line = line
        self.mid = mid
        self.mstr = mstr
        self.fuzzy = fuzzy

    def __repr__(self):
        if self.idmsg == 'extract':
            return self.message + '\n---'
        if self.idmsg == 'compile':
            return '{0}\n{1}'.format('=' * 70, self.message)
        msg = '{0}\n{1}:{2}: [{3}] {4}{5}'.format(
            '=' * 70,
            self.filename,
            self.line,
            self.idmsg,
            '(fuzzy) ' if self.fuzzy else '',
            self.message)
        if self.mid:
            msg += '\n---\n' + self.mid
        if self.mstr:
            msg += '\n---\n' + self.mstr
        return msg


class PoMessage(object):
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

    # pylint: disable=too-many-arguments
    def __init__(self, filename, line, msg, charset, fuzzy):
        """Build a PO message."""
        self.filename = filename
        self.line = line
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

    def check_lines(self):
        """
        Check number of lines in string and translation.
        Return a list with errors detected.
        """
        errors = []
        for mid, mstr in self.messages:
            if not mid or not mstr:
                continue
            nb_id = count_lines(mid)
            nb_str = count_lines(mstr)
            if nb_id != nb_str:
                errors.append(
                    PoReport('number of lines: {0} in string, '
                             '{1} in translation'.format(nb_id, nb_str),
                             'lines', self.filename, self.line, mid, mstr))
        return errors

    def check_punct(self, language):
        """
        Check punctuation at end of string.
        Return a list with errors detected.
        """
        errors = []
        for mid, mstr in self.messages:
            if not mid or not mstr:
                continue
            puncts = [(':', ':'), (';', ';'), (',', ','), ('...', '...')]
            # special symbols in some languages
            if language.startswith('ja'):
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
                    errors.append(
                        PoReport('end punctuation: "{0}" in string, '
                                 '"{1}" not in translation'
                                 ''.format(punctid, punctstr),
                                 'punct', self.filename, self.line, mid, mstr))
                    break
                if not match_id and match_str:
                    errors.append(
                        PoReport('end punctuation: "{0}" in translation, '
                                 '"{1}" not in string'
                                 ''.format(punctstr, punctid),
                                 'punct', self.filename, self.line, mid, mstr))
                    break
        return errors

    def check_whitespace(self):
        """
        Check whitespace at beginning and end of string.
        Return a list with errors detected.
        """
        errors = []
        for mid, mstr in self.messages:
            if not mid or not mstr:
                continue
            # check whitespace at beginning of string
            if count_lines(mid) == 1:
                startin = len(mid) - len(mid.lstrip(' '))
                startout = len(mstr) - len(mstr.lstrip(' '))
                if startin != startout:
                    errors.append(
                        PoReport('whitespace at beginning: {0} in string, '
                                 '{1} in translation'
                                 ''.format(startin, startout),
                                 'whitespace', self.filename, self.line, mid,
                                 mstr))
            # check whitespace at end of string
            endin = len(mid) - len(mid.rstrip(' '))
            endout = len(mstr) - len(mstr.rstrip(' '))
            if endin != endout:
                errors.append(
                    PoReport('whitespace at end: {0} in string, '
                             '{1} in translation'.format(endin, endout),
                             'whitespace', self.filename, self.line, mid,
                             mstr))
        return errors

    def check_whitespace_eol(self):
        """
        Check trailing whitespace at the end of lines in a string.
        Return a list with errors detected.
        """
        errors = []
        for mid, mstr in self.messages:
            if not mid or not mstr:
                continue
            idlines = mid.split('\n')
            strlines = mstr.split('\n')
            if len(idlines) < 2 or len(idlines) != len(strlines):
                continue
            for i in range(0, len(idlines)):
                endin = len(idlines[i]) - len(idlines[i].rstrip(' '))
                endout = len(strlines[i]) - len(strlines[i].rstrip(' '))
                if (endin > 0 or endout > 0) and endin != endout:
                    errors.append(
                        PoReport('different whitespace at end of a line: {0} '
                                 'in string, {1} in translation'
                                 ''.format(endin, endout),
                                 'whitespace_eol', self.filename, self.line,
                                 mid, mstr))
                    break
        return errors

    def check_spelling(self, checkers):
        """
        Check spelling.
        Return a list with errors detected.
        """
        errors = []
        if not checkers:
            return errors
        for mid, mstr in self.messages:
            if not mid or not mstr:
                continue
            checkers[0].set_text(mstr)
            misspelled = []
            for err in checkers[0]:
                misspelled_word = True
                for spell_checker in checkers[1:]:
                    if spell_checker.check(err.word):
                        misspelled_word = False
                        break
                if misspelled_word:
                    misspelled.append(err.word)
            for word in misspelled:
                errors.append(PoReport(word, 'spelling', self.filename,
                                       self.line, mid, mstr))
        return errors


class PoFile(object):
    """
    A gettext file. It includes methods to read the file, and perform
    checks on the translations.
    """

    def __init__(self, filename):
        self.filename = os.path.abspath(filename)
        self.props = {
            'language': '',
            'language_numline': 0,
            'charset': 'utf-8'
        }
        self.msgs = []

    def _add_message(self, numline_msgid, msgfuzzy, msg):
        """
        Add a message from PO file in list of messages.
        """
        if 'msgid' in msg and len(msg['msgid']) == 0:
            # find file language/charset in properties
            # (first string without msgid)
            match = re.search(r'language: ([a-zA-Z-_]+)',
                              msg.get('msgstr', ''), re.IGNORECASE)
            if match:
                self.props['language'] = match.group(1)
                self.props['language_numline'] = numline_msgid
            match = re.search(r'charset=([a-zA-Z0-9-_]+)',
                              msg.get('msgstr', ''), re.IGNORECASE)
            if match:
                self.props['charset'] = match.group(1)
        self.msgs.append(PoMessage(self.filename, numline_msgid, msg,
                                   self.props['charset'], msgfuzzy))

    def read(self):
        """
        Read messages in PO file.
        """
        self.msgs = []
        (numline, numline_msgid) = (0, 0)
        (fuzzy, msgfuzzy) = (False, False)
        msg = {}
        msgcurrent = ''
        with open(self.filename, 'r') as po_file:
            for line in po_file:
                numline += 1
                line = line.strip()
                if len(line) == 0:
                    continue
                if line[0] == '#':
                    fuzzy = 'fuzzy' in line
                    continue
                if line.startswith('msg'):
                    match = re.match(
                        r'([a-zA-Z0-9-_]+(\[\d+\])?)[ \t](.*)',
                        line)
                    if match:
                        oldmsgcurrent = msgcurrent
                        msgcurrent = match.group(1)
                        line = match.group(3)
                        if msgcurrent == 'msgid':
                            if oldmsgcurrent.startswith('msgstr'):
                                self._add_message(numline_msgid,
                                                  msgfuzzy,
                                                  msg)
                            msgfuzzy = fuzzy
                            fuzzy = False
                            msg = {}
                            numline_msgid = numline
                if msgcurrent and line.startswith('"'):
                    msg[msgcurrent] = msg.get(msgcurrent, '') + line[1:-1]
            if msgcurrent.startswith('msgstr'):
                self._add_message(numline_msgid,
                                  msgfuzzy,
                                  msg)

    def compile(self):
        """
        Compile PO file (with msgfmt -c).
        Return a tuple: (output, return code).
        """
        output = ''
        try:
            output = subprocess.check_output(
                ['msgfmt', '-c', '-o', '/dev/null', self.filename],
                stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as exc:
            return (exc.output, exc.returncode)
        return (output, 0)


class PoCheck(object):
    """Perform checks on a gettext file."""

    def __init__(self):
        # checks to perform
        self.checks = {
            'compile': True,
            'fuzzy': False,
            'lines': True,
            'punct': True,
            'whitespace': True,
            'whitespace_eol': True,
            'spelling': False,
            'extract': False,
        }

        # spelling options
        self.dicts = None
        self.extra_checkers = []
        self.pwl = None

    def __repr__(self):
        return ('checks: {self.checks}, '
                'dicts: {self.dicts}, '
                'extra_checkers: {self.extra_checkers}, '
                'pwl: {self.pwl}'.format(self=self))

    def set_check(self, check, state):
        """Enable/disable a specific check."""
        if check in self.checks:
            self.checks[check] = bool(state)

    def set_spelling_options(self, dicts, pwl):
        """Set spelling options."""
        self.dicts = dicts
        self.pwl = pwl

        # check if pwl file exists
        if pwl and not os.path.isfile(pwl):
            raise IOError('pwl file "{0}" not found'.format(pwl))

        # build extra checkers with dicts
        self.extra_checkers = []
        if dicts:
            if not ENCHANT_FOUND:
                raise ImportError('Enchant module not found (please install '
                                  '"pyenchant")')
            for lang in dicts.split(','):
                try:
                    _dict = Dict(lang)
                    self.extra_checkers.append(SpellChecker(_dict))
                except DictNotFoundError:
                    print('WARNING: enchant dictionary not found for '
                          'language "{0}"'.format(lang))

    def _get_language_checker(self, po_file, reports):
        """Get checker for PO file language."""
        checker = []
        if self.checks['spelling']:
            if not ENCHANT_FOUND:
                raise ImportError('Enchant module not found (please install '
                                  '"pyenchant")')
            try:
                _dict = DictWithPWL(po_file.props['language'], self.pwl)
                checker.append(SpellChecker(_dict))
            except DictNotFoundError:
                reports.append(PoReport(
                    'enchant dictionary not found for language "{0}"'
                    ''.format(po_file.props['language']),
                    'dict', po_file.filename,
                    po_file.props['language_numline']))
                checker = []
            except IOError as exc:
                reports.append(PoReport(
                    str(exc), 'pwl', po_file.filename,
                    po_file.props['language_numline']))
                checker = []
        return checker

    def check_pofile(self, po_file):
        """
        Check translations in one PO file.
        Return a list of PoReport objects.
        """

        reports = []

        # build list of checkers (if spelling is enabled)
        checker = self._get_language_checker(po_file, reports)

        # check all messages
        check_fuzzy = self.checks['fuzzy']
        for msg in po_file.msgs:
            if msg.fuzzy and not check_fuzzy:
                continue
            if self.checks['extract']:
                for mid, mstr in msg.messages:
                    if mid and mstr:
                        reports.append(PoReport(mstr, 'extract'))
            else:
                if self.checks['lines']:
                    reports += msg.check_lines()
                if self.checks['punct']:
                    reports += msg.check_punct(po_file.props['language'])
                if self.checks['whitespace']:
                    reports += msg.check_whitespace()
                if self.checks['whitespace_eol']:
                    reports += msg.check_whitespace_eol()
                if self.checks['spelling']:
                    reports += msg.check_spelling(
                        checker + self.extra_checkers)

        return reports

    def check_files(self, files):
        """
        Check translations in PO files.
        Return a list of tuples: (filename, [PoReport, PoReport, ...]).
        """

        result = []

        for filename in files:
            po_file = PoFile(filename)
            # read the file
            try:
                po_file.read()
            except IOError as exc:
                result.append((po_file.filename,
                               [PoReport(str(exc), 'read',
                                         po_file.filename)]))
                continue
            # compile the file (except if disabled)
            compile_output = ''
            compile_rc = 0
            if self.checks['compile']:
                compile_output, compile_rc = po_file.compile()
            if compile_rc == 0:
                # compilation OK
                result.append((po_file.filename, self.check_pofile(po_file)))
            else:
                # compilation failed
                if sys.version_info >= (3,):
                    compile_output = compile_output.decode('utf-8')
                result.append((po_file.filename,
                               [PoReport(compile_output, 'compile',
                                         po_file.filename)]))

        return result
