from pathlib import Path
from tempfile import TemporaryDirectory
import os
import shutil
import unittest

from lunchbox.enforce import EnforceError
import IPython
import lunchbox.tools as lbt
import pandas as pd
import yaml

from rolling_pin.blob_etl import BlobETL
from rolling_pin.conform_etl import ConformETL
import rolling_pin.tools as rpt
# ------------------------------------------------------------------------------


class ConformETLTests(unittest.TestCase):
    def get_conform_repo_path(self):
        if 'REPO_ENV' in os.environ.keys():
            return lbt.relative_path(__file__, '../../resources/conform_repo')
        return lbt.relative_path(__file__, '../resources/conform_repo')

    def get_conform_data_path(self):
        if 'REPO_ENV' in os.environ.keys():
            return lbt.relative_path(__file__, '../../resources/conform_data.csv')
        return lbt.relative_path(__file__, '../resources/conform_data.csv')

    def get_data(self, root):
        data = pd.read_csv(self.get_conform_data_path(), index_col=False)
        data.source = data.source.apply(lambda x: x.format(root=root))
        data.target = data.target.apply(lambda x: x.format(root=root))
        data.groups = data.groups.apply(eval)
        return data

    def get_expected(self, data):
        source = data.source.tolist()
        target = data.target.tolist()
        groups = data.groups.tolist()
        lines = data.line_rule.tolist()
        return source, target, groups, lines

    def get_config(self, source_dir):
        return dict(
            source_rules=[
                dict(path=source_dir, include='README|LICENSE'),
                dict(path=source_dir, include='pdm|pyproject'),
                dict(path=source_dir + '/python', include=r'\.py$', exclude=r'_test'),
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
                dict(group='init', include='baz', exclude='test|ignore'),
            ],
        )

    def setup(self, root):
        repo_path = self.get_conform_repo_path()
        data = self.get_data(root)
        source_dir = Path(root, 'source').as_posix()
        target_dir = Path(root, 'target').as_posix()
        shutil.copytree(repo_path, source_dir)
        config = self.get_config(source_dir)
        return root, source_dir, target_dir, data, config

    # TESTS---------------------------------------------------------------------
    def test_get_data(self):
        with TemporaryDirectory() as root:
            root, _, _, data, config = self.setup(root)
            exp_src, exp_tgt, exp_grp, exp_line = self.get_expected(data)
            data = ConformETL._get_data(**config)

            result = data.columns.tolist()
            self.assertEqual(result, ['source', 'target', 'groups', 'line_rule'])

            # source
            result = data['source'].tolist()
            self.assertEqual(result, exp_src)

            # rename
            result = data['target'].tolist()
            self.assertEqual(result, exp_tgt)

            # group
            result = data['groups'].tolist()
            self.assertEqual(result, exp_grp)

            # line
            result = data['line_rule'].tolist()
            self.assertEqual(result, exp_line)

    def test_init(self):
        with TemporaryDirectory() as root:
            root, _, _, _, config = self.setup(root)
            etl = ConformETL(**config)
            self.assertEqual(etl._data.loc[0, 'line_rule'], False)
            self.assertEqual(etl._line_rules, config['line_rules'])

    def test_init_empty(self):
        with TemporaryDirectory() as root:
            config = self.get_config(root)
            config['source_rules'] = [dict(path=root, include='foobar')]
            result = ConformETL(**config).to_dataframe().shape[0]
            self.assertEqual(result, 0)

    def test_from_yaml(self):
        with TemporaryDirectory() as root:
            config = self.get_config(root)
            config['source_rules'] = config['source_rules'][:2]
            src = Path(root, 'config.YAML').as_posix()
            with open(src, 'w') as f:
                yaml.safe_dump(config, f)
            ConformETL.from_yaml(src)

    def test_from_yaml_error(self):
        expected = '/foo/bar.taco does not end in yml or yaml.'
        with self.assertRaisesRegexp(EnforceError, expected):
            ConformETL.from_yaml('/foo/bar.taco')

    def test_repr(self):
        with TemporaryDirectory() as root:
            *_, config = self.setup(root)
            etl = ConformETL(**config)
            lines = etl.__repr__().split('\n')

            # header
            result = lines[0]
            expected = ' *SOURCE +TARGET +GROUPS +LINE_RULE$'
            self.assertRegex(result, expected)

            # line
            result = lines[1]
            expected = r' */tmp/.*?/source/FAKE-LICENSE'
            expected += r' +/tmp/.*?/target/LICENSE +\[base\] +'
            self.assertRegex(result, expected)

            # line_rule
            result = lines[6]
            expected = r' */tmp/.*?/python/bar/__init__.py'
            expected += r' +/tmp/.*?/target/bar/__init__.py +\[init\] +X'
            self.assertRegex(result, expected)

    def test_groups(self):
        with TemporaryDirectory() as root:
            *_, config = self.setup(root)

            # init
            result = ConformETL(**config).groups
            expected = ['base', 'init']
            self.assertEqual(result, expected)

            # no groups
            config['group_rules'] = []
            result = ConformETL(**config).groups
            expected = ['base']
            self.assertEqual(result, expected)

    def test_to_dataframe(self):
        with TemporaryDirectory() as root:
            *_, config = self.setup(root)

            etl = ConformETL(**config)
            expected = etl._data
            result = etl.to_dataframe()

            self.assertEqual(result.shape, expected.shape)
            self.assertEqual(result.columns.tolist(), expected.columns.tolist())

    def test_to_blob(self):
        with TemporaryDirectory() as root:
            *_, config = self.setup(root)
            etl = ConformETL(**config)

            # instance
            blob = etl.to_blob()
            self.assertIsInstance(blob, BlobETL)

            # keys
            expected = sorted(etl._data.target.tolist())
            result = sorted(list(blob.to_flat_dict().keys()))
            self.assertEqual(result, expected)

            # values
            expected = sorted(etl._data.source.tolist())
            result = sorted(list(blob.to_flat_dict().values()))
            self.assertEqual(result, expected)

    def test_to_html(self):
        with TemporaryDirectory() as root:
            *_, config = self.setup(root)
            result = ConformETL(**config).to_html()
            self.assertIsInstance(result, IPython.display.HTML)

    def test_conform_all(self):
        with TemporaryDirectory() as root:
            _, _, target, _, config = self.setup(root)
            etl = ConformETL(**config)

            etl.conform(groups='all')
            expected = sorted(etl._data['target'].tolist())
            result = sorted([x.as_posix() for x in rpt.list_all_files(target)])
            self.assertEqual(result, expected)

    def test_conform_base(self):
        with TemporaryDirectory() as root:
            _, _, target, _, config = self.setup(root)
            etl = ConformETL(**config)

            etl.conform(groups='base')
            data = etl.to_dataframe()
            mask = data.groups.apply(lambda x: 'base' in x)
            data = data[mask]
            expected = sorted(data['target'].tolist())
            result = sorted([x.as_posix() for x in rpt.list_all_files(target)])
            self.assertEqual(result, expected)

    def test_conform_init(self):
        with TemporaryDirectory() as root:
            _, _, target, _, config = self.setup(root)
            etl = ConformETL(**config)

            etl.conform(groups=['init'])
            data = etl.to_dataframe()
            mask = data.groups.apply(lambda x: 'init' in x)
            data = data[mask]
            expected = sorted(data['target'].tolist())
            result = sorted([x.as_posix() for x in rpt.list_all_files(target)])
            self.assertEqual(result, expected)

    def test_conform_line_rule(self):
        with TemporaryDirectory() as root:
            *_, config = self.setup(root)
            config['group_rules'] = [
                dict(name='test', regex=r'__init__\.py'),
                dict(name='not_test', regex=r'__init__\.py'),
            ]
            config['line_rules'] = [
                dict(group='test', include='test'),
                dict(group='not_test', exclude='test'),
            ]
            etl = ConformETL(**config)

            # test
            etl.conform(groups=['base', 'test'])
            data = etl.to_dataframe()
            target = data[data.line_rule].target.tolist()[0]
            with open(target) as f:
                result = f.read().split('\n')

            expected = ['import baz_testerooni']
            self.assertEqual(result, expected)

            # not_test
            etl.conform(groups=['base', 'not_test'])
            data = etl.to_dataframe()
            target = data[data.line_rule].target.tolist()[0]
            with open(target) as f:
                result = f.read().split('\n')

            expected = [
                'import baz',
                'import ignore',
                'import taco',
                '',
            ]
            self.assertEqual(result, expected)

    def test_conform_line_rule_difference(self):
        with TemporaryDirectory() as root:
            *_, config = self.setup(root)
            config['group_rules'] = [
                dict(name='test', regex=r'__init__\.py'),
                dict(name='not_test', regex=r'__init__\.py'),
            ]
            config['line_rules'] = [
                dict(group='test', include='test'),
                dict(group='not_test', exclude='test'),
            ]
            etl = ConformETL(**config)

            etl.conform(groups=['base', 'test', 'not_test'])
            data = etl.to_dataframe()
            target = data[data.line_rule].target.tolist()[0]
            with open(target) as f:
                result = f.read()

            expected = ''
            self.assertEqual(result, expected)

    def test_conform_line_rule_intersection(self):
        with TemporaryDirectory() as root:
            *_, config = self.setup(root)
            config['group_rules'] = [
                dict(name='foo', regex=r'__init__\.py'),
                dict(name='bar', regex=r'__init__\.py'),
            ]
            config['line_rules'] = [
                dict(group='foo', include='foo|baz'),
                dict(group='bar', include='baz'),
            ]
            etl = ConformETL(**config)

            etl.conform(groups=['base', 'foo', 'bar'])
            data = etl.to_dataframe()
            target = data[data.line_rule].target.tolist()[0]
            with open(target) as f:
                result = f.read().split('\n')

            expected = ['import baz', 'import baz_testerooni']
            self.assertEqual(result, expected)

    def test_conform_line_rule_replace(self):
        with TemporaryDirectory() as root:
            *_, config = self.setup(root)
            config['group_rules'] = [
                dict(name='foo', regex=r'__init__\.py'),
                dict(name='bar', regex=r'__init__\.py'),
            ]
            config['line_rules'] = [
                dict(group='foo', include='taco|baz'),
                dict(group='bar', regex='baz', replace='taco'),
            ]
            etl = ConformETL(**config)

            etl.conform(groups=['base', 'foo', 'bar'])
            data = etl.to_dataframe()
            target = data[data.line_rule].target.tolist()[0]
            with open(target) as f:
                result = f.read().split('\n')

            expected = ['import taco', 'import taco_testerooni', 'import taco']
            self.assertEqual(result, expected)
