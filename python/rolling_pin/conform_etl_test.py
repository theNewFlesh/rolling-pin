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

    def get_args(self, root):
        return dict(
            source_rules=[
                dict(path=root, include='README|LICENSE'),
                dict(path=root, include='pdm|pyproject'),
                dict(path=root + '/python', include=r'\.py$', exclude=r'_test'),
            ],
            rename_rules=[],
            group_rules=[],
            line_rules=[],
        )

    def get_expected_filepaths(self, root):
        return sorted([
            f'{root}/FAKE-LICENSE',
            f'{root}/FAKE-README',
            f'{root}/docker/fake-pdm.lock',
            f'{root}/docker/fake-pdm.toml',
            f'{root}/docker/fake-pyproject.toml',
            f'{root}/python/bar/__init__.py',
            f'{root}/python/bar/baz.py',
            f'{root}/python/foo.py',
        ])

    def get_expected_filepaths_with_tests(self, root):
        return sorted([
            f'{root}/FAKE-LICENSE',
            f'{root}/FAKE-README',
            f'{root}/docker/fake-pdm.lock',
            f'{root}/docker/fake-pdm.toml',
            f'{root}/docker/fake-pyproject.toml',
            f'{root}/python/bar/__init__.py',
            f'{root}/python/bar/baz.py',
            f'{root}/python/bar/baz_testerooni.py',
            f'{root}/python/foo.py',
        ])

    def test_init(self):
        with TemporaryDirectory() as root:
            source = self.create_source_dir(root)
            args = self.get_args(source)
            etl = ConformETL(source_rules=args['source_rules'])
            result = sorted(etl._data['source'].tolist())
            expected = self.get_expected_filepaths(source)
            self.assertEqual(result, expected)
