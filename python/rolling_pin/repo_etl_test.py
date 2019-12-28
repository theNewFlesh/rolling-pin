import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

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
            self.create_repo(root)
            RepoETL(root)

    def test_get_imports(self):
        with TemporaryDirectory() as root:
            self.create_repo(root)
            repo = RepoETL(root)
            module = Path(root, 'a1/b1/m2_test.py')
            result = repo._get_imports(module)
            self.assertEqual(result, ['root.a1.b1.m2', 'pytest'])

    def test_get_data(self):
        pass

    def test_calculate_coordinates(self):
        pass

    def test_anneal_coordinate(self):
        pass

    def test_center_coordinate(self):
        pass

    def test_to_networkx_graph(self):
        pass

    def test_to_dot_graph(self):
        pass

    def test_to_dataframe(self):
        pass

    def test_to_html(self):
        pass

    def test_write(self):
        pass
