from tempfile import TemporaryDirectory
import unittest

from schematics.exceptions import DataError, ValidationError

import rolling_pin.conform_config as rpc
# ------------------------------------------------------------------------------


class ConformETLTests(unittest.TestCase):
    def get_config(self, source_dir):
        return dict(
            source_rules=[
                dict(path=source_dir, include='README|LICENSE'),
                dict(path=source_dir, include='pdm|pyproject'),
                dict(path=source_dir, include='py', exclude='test'),
            ],
            rename_rules=[
                dict(regex='/source', replace='/target'),
                dict(regex='FAKE-|fake-', replace=''),
                dict(regex='/docker', replace=''),
                dict(regex='/python', replace=''),
                dict(regex='/pdm.lock', replace='/.pdm.lock'),
            ],
            group_rules=[
                dict(name='init', regex="__init__.py$"),
                dict(name='test', regex="_test"),
                dict(name='resource', regex="/resources"),
            ],
            line_rules=[
                dict(
                    group='init',
                    include='baz',
                    exclude='test|ignore',
                    regex='foo',
                    replace='taco',
                ),
            ],
        )

    def test_is_dir(self):
        with TemporaryDirectory() as root:
            rpc.is_dir(root)

        expected = '/foo/bar is not a directory or does not exist.'
        with self.assertRaisesRegexp(ValidationError, expected):
            rpc.is_dir('/foo/bar')

    def test_valid(self):
        with TemporaryDirectory() as root:
            config = self.get_config(root)
            rpc.ConformConfig(config).validate()

    def test_source_rule(self):
        with TemporaryDirectory() as root:
            expected = r'source_rules.*This field is required'
            with self.assertRaisesRegexp(DataError, expected):
                rpc.ConformConfig({}).validate()

            config = self.get_config(root)
            config['source_rules'][1]['path'] = '/foobar'
            expected = '/foobar.*is not a directory'
            with self.assertRaisesRegexp(DataError, expected):
                rpc.ConformConfig(config).validate()

    def test_rename_rule(self):
        with TemporaryDirectory() as root:
            config = self.get_config(root)

            # regex
            config['rename_rules'][0] = dict(replace='bar')
            expected = 'regex.*This field is required'
            with self.assertRaisesRegexp(DataError, expected):
                rpc.ConformConfig(config).validate()

            # replace
            config['rename_rules'][0] = dict(regex='foo')
            expected = 'replace.*This field is required'
            with self.assertRaisesRegexp(DataError, expected):
                rpc.ConformConfig(config).validate()

    def test_group_rule(self):
        with TemporaryDirectory() as root:
            config = self.get_config(root)

            # name
            config['group_rules'][0] = dict(regex='bar')
            expected = 'name.*This field is required'
            with self.assertRaisesRegexp(DataError, expected):
                rpc.ConformConfig(config).validate()

            # regex
            config['group_rules'][0] = dict(name='foo')
            expected = 'regex.*This field is required'
            with self.assertRaisesRegexp(DataError, expected):
                rpc.ConformConfig(config).validate()

    def test_line_rule(self):
        with TemporaryDirectory() as root:
            config = self.get_config(root)

            # group
            config['line_rules'][0] = dict(include='foo', exclude='bar')
            expected = 'group.*This field is required'
            with self.assertRaisesRegexp(DataError, expected):
                rpc.ConformConfig(config).validate()
