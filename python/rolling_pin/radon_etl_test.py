import os
import re
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from pandas import DataFrame

import rolling_pin.utils as utils
from rolling_pin.radon_etl import RadonETL
# ------------------------------------------------------------------------------


class RadonEtlTests(unittest.TestCase):
    def get_fake_repo(self):
        return utils.relative_path(__file__, '../../resources/fake_repo')

    def get_fake_repo_data(self):
        data = [
            ['bar/baz.py', 'mod_func_2', np.nan, 'function'],
            ['bar/baz.py', 'cathat', np.nan, 'function'],
            ['foo.py', 'mod_func_1', np.nan, 'function'],
            ['foo.py', '__init__', 'Foo', 'function'],
            ['foo.py', 'do_instance_thing', 'Foo', 'function'],
            ['foo.py', 'do_static_thing', 'Foo', 'function'],
            ['bar/__init__.py', '__init__', np.nan, 'module'],
            ['bar/baz.py', 'baz', np.nan, 'module'],
            ['foo.py', 'foo', np.nan, 'module'],
            ['foo.py', 'recurse', np.nan, 'method_closure'],
            ['foo.py', 'recurse', np.nan, 'closure'],
            ['foo.py', 'Foo', np.nan, 'class'],
        ]
        data = DataFrame(data)
        data.columns = ['fullpath', 'name', 'class_name', 'object_type']
        repo = self.get_fake_repo()
        data.fullpath = data.fullpath\
            .apply(lambda x: Path(repo, x).absolute().as_posix())
        return data

    def assert_equal(self, a, b, cols=['fullpath']):
        self.assertEqual(len(a), len(b))

        a = a.sort_values(cols).reset_index(drop=True)
        b = b.sort_values(cols).reset_index(drop=True)
        for i, row in b.iterrows():
            self.assertEqual(
                a.loc[i, cols].tolist(),
                b.loc[i, cols].tolist(),
            )

    def test_init(self):
        repo = self.get_fake_repo()
        result = RadonETL(repo)._report
        self.assertIsInstance(result, dict)

    def test_report(self):
        repo = self.get_fake_repo()
        result = RadonETL(repo).report

        expected = []
        for name in ['foo.py', 'bar/baz.py', 'bar/__init__.py']:
            temp = Path(repo, name).absolute().as_posix()
            expected.append(temp)

        for key, val in result.items():
            for fullpath in val.keys():
                self.assertIn(fullpath, expected)

    def test_data(self):
        repo = self.get_fake_repo()
        result = RadonETL(repo).data
        expected = self.get_fake_repo_data()
        self.assert_equal(result, expected)

    def test_raw_metrics(self):
        repo = self.get_fake_repo()
        result = RadonETL(repo).raw_metrics.fullpath.tolist()
        expected = self.get_fake_repo_data()
        expected = expected[expected.object_type == 'module']
        expected = expected['fullpath'].tolist()
        self.assertEqual(result, expected)

    def test_maintainability_index(self):
        repo = self.get_fake_repo()
        result = RadonETL(repo).maintainability_index.fullpath.tolist()
        expected = self.get_fake_repo_data()
        expected = expected[expected.object_type == 'module']
        expected = expected['fullpath'].tolist()
        self.assertEqual(result, expected)

    def test_cyclomatic_complexity_metrics(self):
        repo = self.get_fake_repo()
        result = RadonETL(repo).cyclomatic_complexity_metrics
        expected = self.get_fake_repo_data()

        mask = expected.fullpath\
            .apply(lambda x: not re.search('__init__', x))\
            .astype(bool)
        expected = expected[mask]
        mask = expected.object_type\
            .apply(lambda x: not re.search('module', x))\
            .astype(bool)
        expected = expected[mask]
        expected.reset_index(drop=True, inplace=True)

        cols = ['fullpath', 'name', 'class_name']
        self.assert_equal(result, expected, cols)

    def test_halstead_metrics(self):
        repo = self.get_fake_repo()
        result = RadonETL(repo).halstead_metrics
        expected = self.get_fake_repo_data()

        mask = expected.object_type\
            .apply(lambda x: re.search('function|module', x))\
            .astype(bool)
        expected = expected[mask]
        expected.reset_index(drop=True, inplace=True)

        cols = ['fullpath', 'name', 'object_type']
        self.assert_equal(result, expected, cols)

    def test_write_plots(self):
        repo = self.get_fake_repo()
        with TemporaryDirectory() as root:
            target = Path(root, 'foo.html')
            RadonETL(repo).write_plots(target)
            result = sorted(os.listdir(root))
            expected = ['foo.html']
            self.assertEqual(result, expected)

    def test_write_tables(self):
        repo = self.get_fake_repo()
        with TemporaryDirectory() as root:
            RadonETL(repo).write_tables(root)
            result = sorted(os.listdir(root))
            expected = [
                'all_metrics.html',
                'cyclomatic_complexity_metrics.html',
                'halstead_metrics.html',
                'maintainability_metrics.html',
                'raw_metrics.html',
            ]
            self.assertEqual(result, expected)
