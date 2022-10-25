from pathlib import Path
from tempfile import TemporaryDirectory
import os
import shutil
import unittest

import lunchbox.tools as lbt

from rolling_pin.conform_etl import ConformETL
# ------------------------------------------------------------------------------


class ConformETLTests(unittest.TestCase):
    def get_fake_repo(self):
        if 'REPO_ENV' in os.environ.keys():
            return lbt.relative_path(__file__, '../../resources/conform_repo')
        return lbt.relative_path(__file__, '../resources/conform_repo')

    def create_source_dir(self, root):
        repo = self.get_fake_repo()
        src = Path(root, 'source').as_posix()
        shutil.copytree(repo, src)
        return src

    def get_config(self, root):
        return dict(
            source_rules=[
                dict(path=root, include='README|LICENSE'),
                dict(path=root, include='pdm|pyproject'),
                dict(path=root + '/python', include=r'\.py$', exclude=r'_test'),
            ],
            rename_rules=[
                dict(regex='/home/ubuntu/lunchbox', replace='/tmp/repo'),
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

    def get_expected_filepaths(self, source_dir, tests=False):
        output = [
            f'{source_dir}/FAKE-LICENSE',
            f'{source_dir}/FAKE-README',
            f'{source_dir}/docker/fake-pdm.lock',
            f'{source_dir}/docker/fake-pdm.toml',
            f'{source_dir}/docker/fake-pyproject.toml',
            f'{source_dir}/python/bar/__init__.py',
            f'{source_dir}/python/bar/baz.py',
            f'{source_dir}/python/foo.py',
        ]
        if tests:
            output.append(f'{source_dir}/python/bar/baz_testerooni.py')
        return sorted(output)

    def test_init(self):
        with TemporaryDirectory() as root:
            source = self.create_source_dir(root)
            args = self.get_config(source)
            etl = ConformETL(source_rules=args['source_rules'])
            result = sorted(etl._data['source'].tolist())
            expected = self.get_expected_filepaths(source)
            self.assertEqual(result, expected)
