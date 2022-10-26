from pathlib import Path
from tempfile import TemporaryDirectory
import os
import shutil
import unittest

import lunchbox.tools as lbt
import pandas as pd

from rolling_pin.conform_etl import ConformETL
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
                dict(group='init', include=None, exclude='test'),
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

    def test_repr(self):
        with TemporaryDirectory() as root:
            _, _, _, _, config = self.setup(root)
            etl = ConformETL(**config)
            lines = etl.__repr__().split('\n')

            # header
            result = lines[0]
            expected = ' *SOURCE +TARGET +GROUPS +LINE_RULE$'
            self.assertRegex(result, expected)

            # line
            result = lines[1]
            expected = r' */tmp/.*?/source/FAKE-LICENSE +/tmp/.*?/target/LICENSE +\[base\] +'
            self.assertRegex(result, expected)

            # line_rule
            result = lines[6]
            expected = r' */tmp/.*?/python/bar/__init__.py +/tmp/.*?/target/bar/__init__.py +\[init\] +X'
            self.assertRegex(result, expected)

    def test_groups(self):
        with TemporaryDirectory() as root:
            _, _, _, _, config = self.setup(root)

            # init
            result = ConformETL(**config).groups
            expected = ['base', 'init']
            self.assertEqual(result, expected)

            # no groups
            config['group_rules'] = []
            result = ConformETL(**config).groups
            expected = ['base']
            self.assertEqual(result, expected)
