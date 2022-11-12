import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from lunchbox.enforce import EnforceError
from toml.decoder import TomlDecodeError
import toml

from rolling_pin.toml_etl import TomlETL, TomlEtlEncoder
# ------------------------------------------------------------------------------


class TomlEtlEncoderTests(unittest.TestCase):
    def test_init(self):
        result = TomlEtlEncoder().separator
        self.assertEqual(result, ',\n   ')

    def test_dump_list(self):
        result = TomlEtlEncoder().dump_list([])
        self.assertEqual(result, '[]')

        result = TomlEtlEncoder().dump_list([1])
        self.assertEqual(result, '[1]')

        result = TomlEtlEncoder().dump_list(list('abc'))
        expected = '[\n    "a",\n    "b",\n    "c",\n]'
        self.assertEqual(result, expected)


class TomlEtlTests(unittest.TestCase):
    def get_text(self):
        return '''
[root]
a = 1
b = 2

[root.foo.bar]
x = "y"

[world]
hello = true
'''[1:-1]

    def get_data(self):
        return toml.loads(self.get_text())

    def test_init(self):
        expected = self.get_data()
        result = TomlETL(expected)._data
        self.assertEqual(result, expected)

    def test_from_string(self):
        result = TomlETL.from_string(self.get_text())._data
        expected = self.get_data()
        self.assertEqual(result, expected)

    def test_from_toml(self):
        expected = self.get_data()
        with TemporaryDirectory() as root:
            src = Path(root, 'example.toml')
            with open(src, 'w') as f:
                toml.dump(expected, f)

            result = TomlETL.from_toml(src)._data
            self.assertEqual(result, expected)

    def test_to_dict(self):
        expected = self.get_data()
        result = TomlETL(expected).to_dict()
        self.assertEqual(result, expected)

    def test_to_string(self):
        expected = self.get_text()
        result = TomlETL.from_string(expected).to_string()
        self.assertEqual(toml.loads(result), toml.loads(expected))

    def test_write(self):
        expected = self.get_data()
        with TemporaryDirectory() as root:
            tgt = Path(root, 'example.toml')
            TomlETL(expected).write(tgt)
            with open(tgt) as f:
                result = toml.load(f)
            self.assertEqual(result, expected)

    def test_edit(self):
        data = self.get_data()
        etl = TomlETL(data)

        # str
        result = etl.edit('root.a="x"').to_dict()['root']['a']
        self.assertEqual(result, 'x')

        # int
        result = etl.edit('root.a=99').to_dict()['root']['a']
        self.assertEqual(result, 99)

        # float
        result = etl.edit('root.a=99.9').to_dict()['root']['a']
        self.assertEqual(result, 99.9)

        # array
        result = etl.edit('root.a=["a", "b"]').to_dict()['root']['a']
        self.assertEqual(result, ["a", "b"])

        # section
        result = etl.edit('root="x"').to_dict()
        expected = toml.loads('''
            root = "x"
            [world]
            hello = true
        ''')
        self.assertEqual(result, expected)

        # new key
        result = etl.edit('foo.bar="taco"').to_dict()['foo']['bar']
        self.assertEqual(result, 'taco')

    def test_edit_error(self):
        # bad toml
        expected = 'Edit patch must be a TOML parsable key value snippet with a'
        expected += ' "=" character. Found invalid character.*'
        with self.assertRaisesRegex(TomlDecodeError, expected):
            TomlETL(expected).edit('invalid toml')

        # no =
        expected = 'Edit patch must be a TOML parsable key value snippet with a'
        expected += ' "=" character.$'
        with self.assertRaisesRegex(EnforceError, expected):
            TomlETL(expected).edit('[valid-toml]')

    def test_delete(self):
        data = self.get_data()
        etl = TomlETL(data)

        # root key
        result = etl.delete('root').to_dict()
        expected = self.get_data()
        del expected['root']
        self.assertEqual(result, expected)

        # sub key
        result = etl.delete('root.a').to_dict()
        expected = self.get_data()
        del expected['root']['a']
        self.assertEqual(result, expected)

        # non key
        result = etl.delete('root.a.not-a-key').to_dict()
        expected = self.get_data()
        self.assertEqual(result, expected)

    def test_search(self):
        data = self.get_data()
        etl = TomlETL(data)

        # root key
        result = etl.search('root').to_dict()
        expected = dict(root=self.get_data()['root'])
        self.assertEqual(result, expected)

        # sub key
        result = etl.search('root.a').to_dict()
        expected = dict(root=dict(a=self.get_data()['root']['a']))
        self.assertEqual(result, expected)

        # non key
        result = etl.search('root.a.not-a-key').to_dict()
        self.assertEqual(result, {})
