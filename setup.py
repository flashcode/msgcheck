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

from setuptools import setup
from msgcheck.msgcheck import msgcheck_version

DESCRIPTION = 'Perform various checks on gettext files.'
LONG_DESCRIPTION = """
MsgCheck performs various checks on gettext files:

* compilation (with command `msgfmt -c`)
* for each translation:

  - number of lines in translated strings
  - whitespace at beginning/end of strings
  - trailing whitespace at end of lines inside strings
  - punctuation at end of strings
  - spelling (messages and translations).
"""

setup(
    name='msgcheck',
    version=msgcheck_version(),
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    author='Sébastien Helleu',
    author_email='flashcode@flashtux.org',
    url='https://github.com/flashcode/msgcheck',
    license='GPL3',
    keywords='gettext',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 '
        'or later (GPLv3+)',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Localization',
    ],
    packages=['msgcheck'],
    tests_require = ['nose'],
    test_suite = "nose.collector",
    install_requires=['pyenchant'],
    entry_points = {
        'console_scripts': ['msgcheck = msgcheck.msgcheck:main'],
    }
)
