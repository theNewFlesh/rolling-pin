import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from pandas import DataFrame
import pytest

from rolling_pin.repo_etl import RepoETL
# ------------------------------------------------------------------------------


class RepoEtlTests(unittest.TestCase):
    def create_repo(self, root):
        # repo structure
        #       root
        #   ______|____________________
        #   |            |            |
        #   a0           a1        a2.yaml
        #   |         ___|___
        #   |         |     |
        # m0.py     m1.py   b1
        #                ___|______________________
        #                |     |     |            |
        #              m2.p  m3.py  m2_test.py  m3_test.py

        os.makedirs(Path(root, 'a0'))
        os.makedirs(Path(root, 'a1'))
        os.makedirs(Path(root, 'a1/b1'))

        with open(Path(root, 'a0/m0.py'), 'w') as f:
            f.write('\n'.join([
                'import re',
                'from root.a1.m1 import foo',
                'import root.a1.b1.m3',
            ]))

        with open(Path(root, 'a1/m1.py'), 'w') as f:
            f.write('\n'.join([
                'import m0',
                'import m2',
                'import m3',
            ]))

        with open(Path(root, 'a1/b1/m2.py'), 'w') as f:
            f.write('\n'.join([
                'import OpenExr',
                'import m3',
                'from root.a0.m0 import baz',
            ]))

        with open(Path(root, 'a1/b1/m3.py'), 'w') as f:
            f.write('\n'.join(['some python code']))

        with open(Path(root, 'a1/b1/m2_test.py'), 'w') as f:
            f.write('\n'.join([
                'import root.a1.b1.m2 as taco',
                'import re',
                'import pytest',
            ]))

        with open(Path(root, 'a1/b1/m3_test.py'), 'w') as f:
            f.write('\n'.join([
                'import m0',
                'import m3 as pizza',
                'import sys',
                'from collections import OrderedDict',
            ]))

    def test_init(self):
        with TemporaryDirectory() as root:
            expected = f'No files found after filters in directory: {root}.'
            with self.assertRaisesRegex(FileNotFoundError, expected):
                RepoETL(root)

            expected = f'No files found after filters in directory: {root}.'
            with self.assertRaisesRegex(FileNotFoundError, expected):
                RepoETL(root, include_regex=r'foobar\.py$')

            expected = f'No files found after filters in directory: {root}.'
            with self.assertRaisesRegex(FileNotFoundError, expected):
                RepoETL(root, exclude_regex='.*')

            self.create_repo(root)
            RepoETL(root)

    def test_get_imports(self):
        with TemporaryDirectory() as root:
            self.create_repo(root)

            module = Path(root, 'a1/b1/m2_test.py')
            result = RepoETL._get_imports(module)
            self.assertEqual(result, ['root.a1.b1.m2', 'pytest'])

            module = Path(root, 'a1/m1.py')
            result = RepoETL._get_imports(module)
            self.assertEqual(result, ['m0', 'm2', 'm3'])

    def test_get_data(self):
        with TemporaryDirectory() as root:
            self.create_repo(root)
            with pytest.raises(ValueError) as e:
                RepoETL._get_data(root, include_regex='foo')
            expected = "Invalid include_regex: 'foo'. Does not end in '.py$'."
            self.assertEqual(str(e.value), expected)

            result = RepoETL._get_data(root)
            expected = self.get_repo_data(root)
            cols = expected.columns.tolist()
            for i, row in expected.iterrows():
                self.assertEqual(
                    result.loc[i, cols].tolist(),
                    row.tolist()
                )

    def test_calculate_coordinates(self):
        data = self.get_repo_data('/tmp/foo')
        result = RepoETL._calculate_coordinates(data)

        # ensure y axis is stratified according to node type
        mod = result[result.node_type == 'module']
        pkg = result[result.node_type == 'subpackage']
        lib = result[result.node_type == 'library']
        self.assertLess(mod.y.max(), pkg.y.min())
        self.assertLess(pkg.y.max(), lib.y.min())

        # ensure all x ccordinates are unique
        for y in data.y.unique().tolist():
            result = data[data.y == y].x.tolist()
            self.assertCountEqual(result, set(result))

    def test_anneal_coordinate(self):
        data = self.get_repo_data('/tmp/foo')
        data = RepoETL._calculate_coordinates(data)
        data.sort_values('node_name', inplace=True)
        expected = data.y.tolist()
        result = RepoETL._anneal_coordinate(
            data,
            anneal_axis='x',
            pin_axis='y',
            iterations=5,
        )
        result.sort_values('node_name', inplace=True)
        self.assertEqual(result.y.tolist(), expected)

        # ensure all x ccordinates are unique
        for y in data.y.unique().tolist():
            result = data[data.y == y].x.tolist()
            self.assertCountEqual(result, set(result))

    def test_center_coordinate(self):
        data = [
            [0, 0], [1, 0], [2, 0],
            [0, 1], [1, 1], [2, 1], [3, 1], [4, 1],
            [0, 2], [1, 2], [2, 2],
        ]
        data = DataFrame(data, columns=list('xy'))
        expected = [
                    [1, 0], [2, 0], [3, 0],         # noqa E126
            [0, 1], [1, 1], [2, 1], [3, 1], [4, 1], # noqa E126
                    [1, 2], [2, 2], [3, 2],         # noqa E126
        ]
        expected = DataFrame(expected, columns=list('xy'))
        result = RepoETL._center_coordinate(data, center_axis='x', pin_axis='y')
        self.assertEqual(result.x.tolist(), expected.x.tolist())
        self.assertEqual(result.y.tolist(), expected.y.tolist())

    def test_to_networkx_graph(self):
        with TemporaryDirectory() as root:
            self.create_repo(root)
            repo = RepoETL(root)
            data = repo._data
            graph = repo.to_networkx_graph()

            for i, row in data.iterrows():
                name = row['node_name']
                node = graph.nodes[name]

                for col in data.columns:
                    if node[col] is np.nan and row[col] is np.nan:
                        continue
                    self.assertEqual(node[col], row[col])

                for dep in row.dependencies:
                    self.assertTrue(graph.has_edge(dep, name))

            node_count = data.node_name.nunique()
            self.assertEqual(node_count, graph.number_of_nodes())

            edge_count = data.dependencies.apply(len).sum()
            self.assertEqual(edge_count, graph.number_of_edges())


    def test_to_dot_graph(self):
        pass

    def test_to_dataframe(self):
        pass

    def test_to_html(self):
        pass

    def test_write(self):
        pass

    def get_repo_data(self, root):
        cols = [
            'node_name',
            'node_type',
            'dependencies',
            'subpackages',
            'fullpath',
        ]
        data = [
            ['a1.b1.m3', 'module', ['a1.b1'], ['a1', 'a1.b1'], Path(root, 'a1/b1/m3.py')],
            ['a1.m1', 'module', ['m0', 'm2', 'm3', 'a1'], ['a1'], Path(root, 'a1/m1.py')],
            ['a1', 'subpackage', [], [], np.nan],
            ['a1.b1', 'subpackage', ['a1'], ['a1'], np.nan],
            ['OpenExr', 'library', [], [], np.nan],
            ['m0', 'library', [], [], np.nan],
            ['a0', 'subpackage', [], [], np.nan],
            [
                'a1.b1.m2', 'module', ['OpenExr', 'm3', 'root.a0.m0', 'a1.b1'], ['a1', 'a1.b1'],
                Path(root, 'a1/b1/m2.py')
            ],
            ['m2', 'library', [], [], np.nan],
            [
                'a0.m0', 'module', ['root.a1.m1', 'root.a1.b1.m3', 'a0'], ['a0'],
                Path(root, 'a0/m0.py')
            ],
            ['m3', 'library', [], [], np.nan],
            ['root.a0.m0', 'library', [], [], np.nan],
            ['root.a1.b1.m3', 'library', [], [], np.nan],
            ['root.a1.m1', 'library', [], [], np.nan],
        ]
        data = DataFrame(data, columns=cols)
        data.sort_values('fullpath', inplace=True)
        data.reset_index(drop=True, inplace=True)
        return data
