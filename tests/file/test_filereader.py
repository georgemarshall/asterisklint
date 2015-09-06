from io import BytesIO
from unittest import TestCase

from asterisklint.defines import MessageDefManager
from asterisklint.file import FileReader


class NamedBytesIO(BytesIO):
    def __init__(self, name, data):
        super().__init__(data)
        self.name = name


class FileReaderTestCase(TestCase):
    @classmethod
    def setUp(cls):
        MessageDefManager.reset()
        MessageDefManager.muted = True

    def test_normal(self):
        reader = FileReader(NamedBytesIO('test.conf', b'''\
[context]
variable=value
other=value

[context2]
and_that_is=it
'''))
        out = [i for i in reader]
        self.assertEqual(len(out), 6)

        self.assertEqual(out[0][0].filename, 'test.conf')
        self.assertEqual(out[0][0].lineno, 1)
        self.assertEqual(out[0][0].line, b'[context]\n')
        self.assertEqual(out[0][0].last_line, False)
        self.assertEqual(out[0][1], '[context]')

        self.assertEqual(out[1][0].filename, 'test.conf')
        self.assertEqual(out[1][0].lineno, 2)
        self.assertEqual(out[1][0].line, b'variable=value\n')
        self.assertEqual(out[1][0].last_line, False)
        self.assertEqual(out[1][1], 'variable=value')

        self.assertEqual(out[5][0].lineno, 6)
        self.assertEqual(out[5][0].last_line, True)
        self.assertEqual(out[5][1], 'and_that_is=it')

    def test_utf8(self):
        reader = FileReader(NamedBytesIO('utf8.conf', b'''\
[c\xc3\xb6ntext]
variable=value
'''))
        out = [i for i in reader]
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0][1], '[c\u00f6ntext]')

    def test_cp1252(self):
        reader = FileReader(NamedBytesIO('cp1252.conf', b'''\
[cont\x80xt]
variable=value
'''))
        out = [i for i in reader]
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0][1], '[cont\u20acxt]')
        self.assertEqual(
            dict((k, len(v)) for k, v in MessageDefManager.raised.items()),
            {'E_ENC_NOT_UTF8': 1})

    def test_utf8_and_cp1252(self):
        reader = FileReader(NamedBytesIO('encodingmess.conf', b'''\
[c\xc3\xb6nt\x80xt]
variable=value
'''))
        out = [i for i in reader]
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0][1], '[c\u00c3\u00b6nt\u20acxt]')
        self.assertEqual(
            dict((k, len(v)) for k, v in MessageDefManager.raised.items()),
            {'E_ENC_NOT_UTF8': 1})
