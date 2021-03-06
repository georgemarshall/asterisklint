# AsteriskLint -- an Asterisk PBX config syntax checker
# Copyright (C) 2015-2016  Walter Doekes, OSSO B.V.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
from asterisklint import FileConfigParser
from asterisklint.alinttest import ALintTestCase, NamedBytesIO, ignoreLinted


class NormalTest(ALintTestCase):
    def opener(self, filename):
        if filename == 'test.conf':
            return NamedBytesIO(filename, b'''\
[context1]
variable=value
#include "test2.conf"
variable2=value2
''')
        elif filename == 'test2.conf':
            return NamedBytesIO(filename, b'''\
#include "test3.conf"
variable3=value3
variable4=value4
''')
        elif filename == 'test3.conf':
            return NamedBytesIO(filename, b'''\
variable5=value5

[context2]
variable6=value6
''')

    def test_normal(self):
        reader = FileConfigParser(opener=self.opener)
        reader.include('test.conf')

        out = [i for i in reader]
        self.assertEqual([i.name for i in out], ['context1', 'context2'])

        variables = [i for i in out[0]]
        self.assertEqual(
            [(i.where.filename, i.where.lineno, i.variable, i.value)
             for i in variables],
            [('test.conf', 2, 'variable', 'value'),
             ('test3.conf', 1, 'variable5', 'value5')])

        variables = [i for i in out[1]]
        self.assertEqual(
            [(i.where.filename, i.where.lineno, i.variable, i.value)
             for i in variables],
            [('test3.conf', 4, 'variable6', 'value6'),
             ('test2.conf', 2, 'variable3', 'value3'),
             ('test2.conf', 3, 'variable4', 'value4'),
             ('test.conf', 4, 'variable2', 'value2')])


class LineNumberTest(ALintTestCase):
    """
    Initially, there was a bug, where the variable=value on line 3 would
    get marked as being on line 2. Test that that's fixed.
    """
    def opener(self, filename):
        if filename == 'test.conf':
            return NamedBytesIO(filename, b'''\
[context1]
#include "test2.conf"
variable=value  ; line 3
''')
        elif filename == 'test2.conf':
            return NamedBytesIO(filename, b'''\
variable2=value2
''')

    def test_correct_linenumber(self):
        reader = FileConfigParser(opener=self.opener)
        reader.include('test.conf')

        out = [i for i in reader]
        self.assertEqual([i.name for i in out], ['context1'])

        variables = [i for i in out[0]]
        self.assertEqual(
            [(i.where.filename, i.where.lineno, i.variable, i.value)
             for i in variables],
            [('test2.conf', 1, 'variable2', 'value2'),
             ('test.conf', 3, 'variable', 'value')])


class WithBlanksTest(ALintTestCase):
    def opener(self, filename):
        if filename == 'test.conf':
            return NamedBytesIO(filename, b'''\
  [context1]
 variable=value
   #include\x01\x02"test2.conf"
variable2=value2  ; line 4 (and not line 3, keep this test!)
''')
        elif filename == 'test2.conf':
            return NamedBytesIO(filename, b'''\
  variable3 = value3
  ; this is line 2
 variable4 = value4
''')

    def test_with_leading_blanks(self):
        reader = FileConfigParser(opener=self.opener)
        reader.include('test.conf')

        out = [i for i in reader]
        self.assertEqual([i.name for i in out], ['context1'])

        variables = [i for i in out[0]]
        self.assertEqual(
            [(i.where.filename, i.where.lineno, i.variable, i.value)
             for i in variables],
            [('test.conf', 2, 'variable', 'value'),
             ('test2.conf', 1, 'variable3', 'value3'),
             ('test2.conf', 3, 'variable4', 'value4'),
             ('test.conf', 4, 'variable2', 'value2')])

        self.assertLinted({'W_FILE_CTRL_CHAR': 1, 'W_WSH_BOL': 5,
                           'W_WSH_CTRL': 1, 'W_WSH_VARSET': 2})


class WhiteSpaceInIncludesTest(ALintTestCase):
    def opener(self, filename):
        if filename == 'test.conf':
            return NamedBytesIO(filename, b'''\


[context1]
variable=value
#include "test2.conf"

[context3]
variable3=value3


''')
        elif filename == 'test2.conf':
            return NamedBytesIO(filename, b'''\


[context2]
variable2=value2


''')

    @ignoreLinted('H_WSV_CTX_BETWEEN')  # don't care about this now
    def test_with_two_bof_eof_warnings(self):
        reader = FileConfigParser(opener=self.opener)
        reader.include('test.conf')

        out = [i for i in reader]
        self.assertEqual([i.name for i in out],
                         ['context1', 'context2', 'context3'])

        variables = [i for i in out[0]]
        self.assertEqual(
            [(i.where.filename, i.where.lineno, i.variable, i.value)
             for i in variables],
            [('test.conf', 4, 'variable', 'value')])
        variables = [i for i in out[1]]
        self.assertEqual(
            [(i.where.filename, i.where.lineno, i.variable, i.value)
             for i in variables],
            [('test2.conf', 4, 'variable2', 'value2')])
        variables = [i for i in out[2]]
        self.assertEqual(
            [(i.where.filename, i.where.lineno, i.variable, i.value)
             for i in variables],
            [('test.conf', 8, 'variable3', 'value3')])

        self.assertLinted({'W_WSV_BOF': 2, 'W_WSV_EOF': 2})


class IncludeFileLastTest(ALintTestCase):
    def opener(self, filename, extra_space=b''):
        if filename == 'test.conf':
            return NamedBytesIO(filename, b'''\
[context1]
variable=value

#include "test2.conf"
''' + extra_space)
        elif filename == 'test2.conf':
            return NamedBytesIO(filename, b'''\
[context2]
variable2=value2
''')

    def opener_with_extra_space(self, filename):
        return self.opener(filename, extra_space=b'\n')

    def test_that_this_yields_no_lint_messages(self):
        reader = FileConfigParser(opener=self.opener)
        reader.include('test.conf')
        out = [i for i in reader]
        del out
        self.assertLinted({})  # *not* W_WSV_EOF

    def test_that_this_yields_an_eof_lint_message(self):
        reader = FileConfigParser(opener=self.opener_with_extra_space)
        reader.include('test.conf')
        out = [i for i in reader]
        del out
        self.assertLinted({'W_WSV_EOF': 1})
