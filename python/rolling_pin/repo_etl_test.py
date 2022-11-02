from pathlib import Path
from tempfile import TemporaryDirectory
import os
import unittest

from pandas import DataFrame
import IPython
import lunchbox.tools as lbt
import numpy as np
import pytest

import rolling_pin.repo_etl as rpo
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
                rpo.RepoETL(root)

            expected = f'No files found after filters in directory: {root}.'
            with self.assertRaisesRegex(FileNotFoundError, expected):
                rpo.RepoETL(root, include_regex=r'foobar\.py$')

            expected = f'No files found after filters in directory: {root}.'
            with self.assertRaisesRegex(FileNotFoundError, expected):
                rpo.RepoETL(root, exclude_regex='.*')

            self.create_repo(root)
            rpo.RepoETL(root)

    def test_get_imports(self):
        with TemporaryDirectory() as root:
            self.create_repo(root)

            module = Path(root, 'a1/b1/m2_test.py')
            result = rpo.RepoETL._get_imports(module)
            self.assertEqual(result, ['root.a1.b1.m2', 'pytest'])

            module = Path(root, 'a1/m1.py')
            result = rpo.RepoETL._get_imports(module)
            self.assertEqual(result, ['m0', 'm2', 'm3'])

    def test_get_data(self):
        with TemporaryDirectory() as root:
            self.create_repo(root)
            with pytest.raises(ValueError) as e:
                rpo.RepoETL._get_data(Path(root), include_regex='foo')
            expected = "Invalid include_regex: 'foo'. Does not end in '.py$'."
            self.assertEqual(str(e.value), expected)

            result = rpo.RepoETL._get_data(root)
            expected = self.get_repo_data(root)
            cols = expected.columns.tolist()
            for i, row in expected.iterrows():
                self.assertEqual(
                    result.loc[i, cols].tolist(),
                    row.tolist()
                )

    def test_calculate_coordinates(self):
        data = self.get_repo_data('/tmp/foo')
        result = rpo.RepoETL._calculate_coordinates(data)

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
        data = rpo.RepoETL._calculate_coordinates(data)
        data.sort_values('node_name', inplace=True)
        expected = data.y.tolist()
        result = rpo.RepoETL._anneal_coordinate(
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
        result = rpo.RepoETL._center_coordinate(data, center_axis='x', pin_axis='y')
        self.assertEqual(result.x.tolist(), expected.x.tolist())
        self.assertEqual(result.y.tolist(), expected.y.tolist())

    def test_to_networkx_graph(self):
        with TemporaryDirectory() as root:
            self.create_repo(root)
            repo = rpo.RepoETL(root)
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

    def test_to_dot_graph_error(self):
        with TemporaryDirectory() as root:
            self.create_repo(root)

            with pytest.raises(ValueError) as e:
                rpo.RepoETL(root).to_dot_graph(orient='foo')
            expected = "Invalid orient value. foo not in ['tb', 'bt', 'lr', 'rl']."
            self.assertEqual(str(e.value), expected)

    def test_to_dot_graph(self):
        color_scheme = dict(
            background='#F00000',
            node='#FF0000',
            node_font='#FFF000',
            edge='#FFFF00',
            node_library_font='#FFFFF0',
            node_subpackage_font='#FFFFFF',
            node_module_font='#AAAAAA',
            edge_library='#BBBBBB',
            edge_subpackage='#CCCCCC',
            edge_module='#DDDDDD',
        )
        with TemporaryDirectory() as root:
            self.create_repo(root)
            repo = rpo.RepoETL(root)

            result = repo.to_dot_graph(orthogonal_edges=True)
            self.assertEqual(result.get_splines(), 'ortho')

            result = repo.to_dot_graph(color_scheme=color_scheme)
            self.assertEqual(result.get_bgcolor(), color_scheme['background'])

            for node in result.get_nodes():
                self.assertEqual(node.get_color(), color_scheme['node'])
                self.assertEqual(node.get_fillcolor(), color_scheme['node'])

                # vary node font color by noe type
                attrs = node.get_attributes()
                if attrs['node_type'] == 'library':
                    self.assertEqual(
                        node.get_fontcolor(),
                        color_scheme['node_library_font']
                    )
                elif attrs['node_type'] == 'subpackage':
                    self.assertEqual(
                        node.get_fontcolor(),
                        color_scheme['node_subpackage_font']
                    )
                else:
                    self.assertEqual(
                        node.get_fontcolor(),
                        color_scheme['node_module_font']
                    )

            for edge in result.get_edges():
                node = result.get_node(edge.get_source())[0]
                node = result.get_node(node.get_name())[0]
                attrs = node.get_attributes()

                if attrs['node_type'] == 'library':
                    self.assertEqual(
                        edge.get_color(),
                        color_scheme['edge_library']
                    )
                elif attrs['node_type'] == 'subpackage':
                    self.assertEqual(
                        edge.get_color(),
                        color_scheme['edge_subpackage']
                    )
                else:
                    self.assertEqual(
                        edge.get_color(),
                        color_scheme['edge_module']
                    )

    def test_to_dataframe(self):
        with TemporaryDirectory() as root:
            self.create_repo(root)
            repo = rpo.RepoETL(root)
            result = repo.to_dataframe()
            self.assertIsNot(result, repo._data)

    def test_to_html(self):
        with TemporaryDirectory() as root:
            self.create_repo(root)
            repo = rpo.RepoETL(root)
            result = repo.to_html()
            self.assertIsInstance(result, IPython.display.HTML)

    def test_write(self):
        with TemporaryDirectory() as root:
            self.create_repo(root)
            repo = rpo.RepoETL(root)

            result = Path(root, 'foo.svg')
            repo.write(result)
            self.assertTrue(os.path.exists(result))

            result = Path(root, 'foo.dot')
            repo.write(result)
            self.assertTrue(os.path.exists(result))

            result = Path(root, 'foo.png')
            repo.write(result)
            self.assertTrue(os.path.exists(result))

            result = Path(root, 'foo.json').absolute().as_posix()
            repo.write(result)
            self.assertTrue(os.path.exists(result))

            with pytest.raises(ValueError) as e:
                repo.write(Path(root, 'foo.bar'))
            expected = 'Invalid extension found: bar. Valid extensions '
            expected += 'include: svg, dot, png, json.'
            self.assertEqual(str(e.value), expected)

    def get_repo_data(self, root):
        cols = [
            'node_name',
            'node_type',
            'dependencies',
            'subpackages',
            'fullpath',
        ]
        data = [
            [
                'a1.b1.m3', 'module', ['a1.b1'], ['a1', 'a1.b1'],
                Path(root, 'a1/b1/m3.py').absolute().as_posix()
            ],
            [
                'a1.m1', 'module', ['m0', 'm2', 'm3', 'a1'], ['a1'],
                Path(root, 'a1/m1.py').absolute().as_posix()
            ],
            ['a1', 'subpackage', [], [], np.nan],
            ['a1.b1', 'subpackage', ['a1'], ['a1'], np.nan],
            ['OpenExr', 'library', [], [], np.nan],
            ['m0', 'library', [], [], np.nan],
            ['a0', 'subpackage', [], [], np.nan],
            [
                'a1.b1.m2', 'module', ['OpenExr', 'm3', 'root.a0.m0', 'a1.b1'], ['a1', 'a1.b1'],
                Path(root, 'a1/b1/m2.py').absolute().as_posix()
            ],
            ['m2', 'library', [], [], np.nan],
            [
                'a0.m0', 'module', ['root.a1.m1', 'root.a1.b1.m3', 'a0'], ['a0'],
                Path(root, 'a0/m0.py').absolute().as_posix()
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
# ------------------------------------------------------------------------------


class RepoEtlFuncTests(unittest.TestCase):
    def get_fake_repo(self):
        return lbt.relative_path(__file__, '../resources/fake_repo')

    def test_write_repo_plots_and_tables(self):
        with TemporaryDirectory() as root:
            repo = self.get_fake_repo()
            tables = Path(root, 'tables')
            os.makedirs(tables)
            plot = Path(root, 'plot.html')

            # write plots
            rpo.write_repo_plots_and_tables(repo, plot, tables)
            result = sorted(os.listdir(tables))
            expected = [
                'all_metrics.html',
                'cyclomatic_complexity_metrics.html',
                'halstead_metrics.html',
                'maintainability_metrics.html',
                'raw_metrics.html',
            ]
            self.assertEqual(result, expected)
            self.assertTrue(plot.is_file())

    def test_write_repo_architecture(self):
        with TemporaryDirectory() as root:
            source = self.get_fake_repo()
            target = Path(root, 'architecture.svg')
            rpo.write_repo_architecture(source, target)
            self.assertTrue(target.is_file())
