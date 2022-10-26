import json
import os
import unittest
from collections import OrderedDict
from pathlib import Path
from tempfile import TemporaryDirectory

from pandas import DataFrame
import pydot
import pytest

import rolling_pin.tools as rpt
# ------------------------------------------------------------------------------


class ToolsTests(unittest.TestCase):
    def get_simple_blob(self):
        data = {
            'a0': {
                'b0': {
                    'c0': 'a0/b0/c0/value',
                    'c1': 'a0/b0/c1/value',
                },
                'b1': {
                    'c0': 'a0/b1/c0/value',
                }
            }
        }
        return data

    def get_complex_blob(self):
        data = {
            'a0': {
                'b0': {
                    'c0': 'a0/b0/c0/value',
                    'c1': 'a0/b0/c1/value',
                },
                'b1': [
                    {
                        'c0': 'a0/b1/c0/value',
                        'c1': 'a0/b1/c1/value',
                    },
                    {
                        'c2': 'a0/b1/c2/value',
                        'c3': {
                            'd0': [
                                set([
                                    'a0/b1/c3/d0/value'
                                ]),
                                tuple([
                                    'a0/b1/c3/d0/value0',
                                    'a0/b1/c3/d0/value1',
                                ]),
                            ]
                        }
                    },
                ]
            }
        }
        return data

    def get_nested_dict(self):
        output = {
            'a0': {
                'b0': {
                    'c0': 0
                },
                'b1': {
                    'c0': 1,
                    'c1': 2,
                }
            }
        }
        return output

    # GENERAL-------------------------------------------------------------------
    def test_is_iterable(self):
        self.assertTrue(rpt.is_iterable({}))
        self.assertTrue(rpt.is_iterable(OrderedDict({})))
        self.assertTrue(rpt.is_iterable([]))
        self.assertTrue(rpt.is_iterable(set()))
        self.assertTrue(rpt.is_iterable(tuple()))

        self.assertTrue(rpt.is_iterable([
            ('k0', 'v0'),
            ('k1', 'v1'),
        ]))
        self.assertFalse(rpt.is_iterable(
            json.dumps({'a': 'b'})
        ))
        self.assertFalse(rpt.is_iterable('foo'))

    # PREDICATE-FUNCTIONS-------------------------------------------------------
    def test_is_dictlike(self):
        self.assertTrue(rpt.is_dictlike({}))
        self.assertTrue(rpt.is_dictlike(OrderedDict({})))

        self.assertFalse(rpt.is_dictlike(
            json.dumps({'a': 'b'})
        ))
        self.assertFalse(rpt.is_dictlike([
            ('k0', 'v0'),
            ('k1', 'v1'),
        ]))
        self.assertFalse(rpt.is_dictlike([]))
        self.assertFalse(rpt.is_dictlike(set()))
        self.assertFalse(rpt.is_dictlike(tuple()))
        self.assertFalse(rpt.is_dictlike('foo'))

    def test_is_listlike(self):
        self.assertTrue(rpt.is_listlike([]))
        self.assertTrue(rpt.is_listlike(set()))
        self.assertTrue(rpt.is_listlike(tuple()))
        self.assertTrue(rpt.is_listlike([
            ('k0', 'v0'),
            ('k1', 'v1'),
        ]))

        self.assertFalse(rpt.is_listlike({}))
        self.assertFalse(rpt.is_listlike(OrderedDict({})))
        self.assertFalse(rpt.is_listlike(
            json.dumps({'a': 'b'})
        ))
        self.assertFalse(rpt.is_listlike('foo'))

    # FLATTEN-------------------------------------------------------------------
    def test_flatten_simple(self):
        data = self.get_simple_blob()
        expected = {
            'a0/b0/c0': 'a0/b0/c0/value',
            'a0/b0/c1': 'a0/b0/c1/value',
            'a0/b1/c0': 'a0/b1/c0/value',
        }
        result = rpt.flatten(data)
        self.assertEqual(result, expected)

    def test_flatten_simple_separator(self):
        blob = self.get_simple_blob()
        expected = {
            'a0_b0_c0': 'a0/b0/c0/value',
            'a0_b0_c1': 'a0/b0/c1/value',
            'a0_b1_c0': 'a0/b1/c0/value',
        }
        result = rpt.flatten(blob, separator='_')
        self.assertEqual(result, expected)

    def test_flatten_complex(self):
        blob = self.get_complex_blob()
        expected = {
            'a0/b0/c0': 'a0/b0/c0/value',
            'a0/b0/c1': 'a0/b0/c1/value',
            'a0/b1/<list_0>/c0': 'a0/b1/c0/value',
            'a0/b1/<list_0>/c1': 'a0/b1/c1/value',
            'a0/b1/<list_1>/c2': 'a0/b1/c2/value',
            'a0/b1/<list_1>/c3/d0/<list_0>/<set_0>': 'a0/b1/c3/d0/value',
            'a0/b1/<list_1>/c3/d0/<list_1>/<tuple_0>': 'a0/b1/c3/d0/value0',
            'a0/b1/<list_1>/c3/d0/<list_1>/<tuple_1>': 'a0/b1/c3/d0/value1',
        }
        result = rpt.flatten(blob, embed_types=True)
        self.assertEqual(result, expected)

    def test_flatten_complex_separator(self):
        blob = self.get_complex_blob()
        expected = {
            'a0=>b0=>c0': 'a0/b0/c0/value',
            'a0=>b0=>c1': 'a0/b0/c1/value',
            'a0=>b1=><list_0>=>c0': 'a0/b1/c0/value',
            'a0=>b1=><list_0>=>c1': 'a0/b1/c1/value',
            'a0=>b1=><list_1>=>c2': 'a0/b1/c2/value',
            'a0=>b1=><list_1>=>c3=>d0=><list_0>=><set_0>': 'a0/b1/c3/d0/value',
            'a0=>b1=><list_1>=>c3=>d0=><list_1>=><tuple_0>': 'a0/b1/c3/d0/value0',
            'a0=>b1=><list_1>=>c3=>d0=><list_1>=><tuple_1>': 'a0/b1/c3/d0/value1',
        }
        result = rpt.flatten(blob, separator='=>')
        self.assertEqual(result, expected)

    def test_flatten_complex_no_embed(self):
        blob = self.get_complex_blob()
        expected = {
            'a0/b0/c0': 'a0/b0/c0/value',
            'a0/b0/c1': 'a0/b0/c1/value',
            'a0/b1/0/c0': 'a0/b1/c0/value',
            'a0/b1/0/c1': 'a0/b1/c1/value',
            'a0/b1/1/c2': 'a0/b1/c2/value',
            'a0/b1/1/c3/d0/0/0': 'a0/b1/c3/d0/value',
            'a0/b1/1/c3/d0/1/0': 'a0/b1/c3/d0/value0',
            'a0/b1/1/c3/d0/1/1': 'a0/b1/c3/d0/value1',
        }
        result = rpt.flatten(blob, embed_types=False)
        self.assertEqual(result, expected)

    def test_flatten_complex_separator_no_embed(self):
        blob = self.get_complex_blob()
        expected = {
            'a0=>b0=>c0': 'a0/b0/c0/value',
            'a0=>b0=>c1': 'a0/b0/c1/value',
            'a0=>b1=>0=>c0': 'a0/b1/c0/value',
            'a0=>b1=>0=>c1': 'a0/b1/c1/value',
            'a0=>b1=>1=>c2': 'a0/b1/c2/value',
            'a0=>b1=>1=>c3=>d0=>0=>0': 'a0/b1/c3/d0/value',
            'a0=>b1=>1=>c3=>d0=>1=>0': 'a0/b1/c3/d0/value0',
            'a0=>b1=>1=>c3=>d0=>1=>1': 'a0/b1/c3/d0/value1',
        }
        result = rpt.flatten(blob, separator='=>', embed_types=False)
        self.assertEqual(result, expected)

    def test_flatten_double(self):
        expected = {
            'a0/b0/c0': 'a0/b0/c0/value',
            'a0/b0/c1': 'a0/b0/c1/value',
            'a0/b1/c0': 'a0/b1/c0/value',
        }
        result = rpt.flatten(expected)
        result = rpt.flatten(result)
        self.assertEqual(result, expected)

    # NEST----------------------------------------------------------------------
    def test_nest(self):
        blob = {
            'a0/b0/c0': 0,
            'a0/b1/c0': 1,
            'a0/b1/c1': 2,
        }
        expected = self.get_nested_dict()
        result = rpt.nest(blob)
        self.assertEqual(result, expected)

        blob = {
            'foo': 0,
            'bar': 0,
            'foo/bar': 0,
        }
        expected = "Duplicate key conflict. Key: 'foo'."
        with self.assertRaisesRegex(KeyError, expected):
            rpt.nest(blob)

    def test_nest_separator(self):
        blob = {
            'a0-b0-c0': 0,
            'a0-b1-c0': 1,
            'a0-b1-c1': 2,
        }
        expected = self.get_nested_dict()
        result = rpt.nest(blob, separator='-')
        self.assertEqual(result, expected)

    def test_nest_double(self):
        expected = self.get_nested_dict()
        result = rpt.nest(expected)
        result = rpt.nest(result)
        self.assertEqual(result, expected)

    # UNEMBED-------------------------------------------------------------------
    def test_unembed(self):
        blob = {
            'a0': {
                'b0': {
                    'c0': 0,
                    'c1': {
                        '<set_0>': 0,
                        '<set_1>': 1,
                    },
                },
                'b1': {
                    '<list_0>': 2,
                    '<list_1>': 3,
                }
            }
        }
        expected = {
            'a0': {
                'b0': {
                    'c0': 0,
                    'c1': set([0, 1])
                },
                'b1': [2, 3],
            }
        }
        result = rpt.unembed(blob)
        self.assertEqual(result, expected)

    def test_unembed_nest_flatten_cycle(self):
        expected = self.get_complex_blob()
        result = rpt.unembed(rpt.nest(rpt.flatten(expected)))
        result = rpt.unembed(rpt.nest(rpt.flatten(result)))
        self.assertEqual(result, expected)
        self.assertFalse(result is expected)

    # MISC----------------------------------------------------------------------
    def test_list_all_files(self):
        # repo structure
        #       root
        #   ______|______
        #   |           |
        #   a0          a1
        #   |        ___|___
        #   |        |     |
        # m0.py    m1.py   b1
        #               ___|___
        #               |     |
        #             m2.p  m3.py
        with TemporaryDirectory() as root:
            os.makedirs(Path(root, 'a0'))
            os.makedirs(Path(root, 'a1'))
            os.makedirs(Path(root, 'a1/b1'))

            with open(Path(root, 'a0/m0.py'), 'w') as f:
                f.writelines([
                    'from root.a1.m1 import foo',
                    'import root.a1.b1.m3',
                ])

            with open(Path(root, 'a1/m1.py'), 'w') as f:
                f.writelines([
                    'import m0',
                    'import m2',
                    'import m3',
                ])

            with open(Path(root, 'a1/b1/m2.py'), 'w') as f:
                f.writelines([
                    'import m3',
                    'from root.a0.m0 import baz',
                ])

            with open(Path(root, 'a1/b1/m3.py'), 'w') as f:
                f.writelines(['some python code'])

            result = rpt.list_all_files(root)
            expected = [
                Path(root, 'a0/m0.py'),
                Path(root, 'a1/m1.py'),
                Path(root, 'a1/b1/m2.py'),
                Path(root, 'a1/b1/m3.py'),
            ]
            for item in expected:
                self.assertIn(item, result)

    def create_files(self, root):
        filepaths = [
            'a/1.foo',
            'a/b/2.json',
            'a/b/3.txt',
            'a/b/c/4.json',
            'a/b/c/5.txt'
        ]
        filepaths = [Path(root, x) for x in filepaths]
        for filepath in filepaths:
            os.makedirs(filepath.parent, exist_ok=True)
            with open(filepath, 'w') as f:
                f.write('')
        return filepaths

    def test_list_all_files_errors(self):
        expected = '/foo/bar is not a directory or does not exist.'
        with self.assertRaisesRegexp(FileNotFoundError, expected):
            next(rpt.list_all_files('/foo/bar'))

        expected = '/foo.bar is not a directory or does not exist.'
        with self.assertRaisesRegexp(FileNotFoundError, expected):
            next(rpt.list_all_files('/foo.bar'))

        with TemporaryDirectory() as root:
            expected = sorted(self.create_files(root))
            result = sorted(list(rpt.list_all_files(root)))
            self.assertEqual(result, expected)

    def test_list_all_files_include(self):
        with TemporaryDirectory() as root:
            regex = r'\.txt'

            self.create_files(root)
            expected = [
                Path(root, 'a/b/3.txt'),
                Path(root, 'a/b/c/5.txt'),
            ]

            result = rpt.list_all_files(root, include_regex=regex)
            result = sorted(list(result))
            self.assertEqual(result, expected)

    def test_list_all_files_exclude(self):
        with TemporaryDirectory() as root:
            regex = r'\.txt'

            self.create_files(root)
            expected = [
                Path(root, 'a/1.foo'),
                Path(root, 'a/b/2.json'),
                Path(root, 'a/b/c/4.json'),
            ]

            result = rpt.list_all_files(root, exclude_regex=regex)
            result = sorted(list(result))
            self.assertEqual(result, expected)

    def test_list_all_files_include_exclude(self):
        with TemporaryDirectory() as root:
            i_regex = r'/a/b'
            e_regex = r'\.json'

            self.create_files(root)
            expected = [
                Path(root, 'a/b/3.txt'),
                Path(root, 'a/b/c/5.txt'),
            ]

            result = rpt.list_all_files(
                root,
                include_regex=i_regex,
                exclude_regex=e_regex
            )
            result = sorted(list(result))
            self.assertEqual(result, expected)

    def test_get_parent_fields(self):
        result = rpt.get_parent_fields('a/b/c/d')
        expected = ['a', 'a/b', 'a/b/c']
        self.assertEqual(result, expected)

        result = rpt.get_parent_fields('a-b-c-d', separator='-')
        expected = ['a', 'a-b', 'a-b-c']
        self.assertEqual(result, expected)

    def test_dot_to_html(self):
        dot = pydot.Dot()
        with pytest.raises(ValueError) as e:
            rpt.dot_to_html(dot, layout='foo')
        expected = 'Invalid layout value. foo not in '
        expected += "['circo', 'dot', 'fdp', 'neato', 'sfdp', 'twopi']."
        self.assertEqual(str(e.value), expected)

        rpt.dot_to_html(dot)
        rpt.dot_to_html(dot, as_png=True)

    def test_write_dot_graph(self):
        expected = 'Invalid extension found: bar. '
        expected += 'Valid extensions include: svg, dot, png.'
        with pytest.raises(ValueError) as e:
            rpt.write_dot_graph(pydot.Dot(), '/tmp/foo.bar')
        self.assertEqual(str(e.value), expected)

        with TemporaryDirectory() as root:
            for ext in ['SVG', 'dot', 'pNg']:
                result = Path(root, 'foo.' + ext)
                rpt.write_dot_graph(pydot.Dot(), result)
                self.assertTrue(os.path.exists(result))

    def test_directory_to_dataframe(self):
        with TemporaryDirectory() as root:
            self.create_files(root)
            filepaths = [
                Path(root, 'a/b/3.txt'),
                Path(root, 'a/b/c/5.txt'),
            ]
            expected = DataFrame()
            expected['filepath'] = filepaths
            expected['filename'] = expected.filepath.apply(lambda x: x.name)
            expected['extension'] = 'txt'
            expected.filepath = expected.filepath.apply(lambda x: x.as_posix())

            result = rpt.directory_to_dataframe(
                root,
                include_regex=r'/a/b',
                exclude_regex=r'\.json'
            )
            cols = ['filepath', 'filename', 'extension']
            for col in cols:
                self.assertEqual(result[col].tolist(), expected[col].tolist())

    def test_filter_text(self):
        text = 'foo\nbar\nbaz\nfoo'

        # identity
        result = rpt.filter_text(text)
        self.assertEqual(result, text)

        # include
        expected = 'foo\nbar\nfoo'
        result = rpt.filter_text(text, include_regex='bar|foo')
        self.assertEqual(result, expected)

        # exclude
        expected = 'bar\nbaz'
        result = rpt.filter_text(text, exclude_regex='foo')
        self.assertEqual(result, expected)

        # include exclude
        expected = 'baz'
        result = rpt.filter_text(text, include_regex='foo|baz', exclude_regex='foo')
        self.assertEqual(result, expected)

        # include exclude conflict
        expected = ''
        result = rpt.filter_text(text, include_regex='foo', exclude_regex='foo')
        self.assertEqual(result, expected)

    def test_read_text(self):
        with TemporaryDirectory() as root:
            src = Path(root, 'foo.txt')
            with self.assertRaises(AssertionError):
                rpt.read_text(src)

            expected = 'a\nb\nc'
            with open(src, 'w') as f:
                f.write(expected)
            result = rpt.read_text(src)
            self.assertEqual(result, expected)

    def test_write_text(self):
        with TemporaryDirectory() as root:
            src = Path(root, 'foo.txt')
            expected = 'a\nb\nc'
            rpt.write_text(expected, src)

            with open(src) as f:
                result = f.read()
            self.assertEqual(result, expected)

    def test_copy_file(self):
        with TemporaryDirectory() as root:
            src = Path(root, 'src.txt')
            tgt = Path(root, 'target', 'tgt.txt')
            with open(src, 'w') as f:
                f.write('foo\nbar')
            rpt.copy_file(src, tgt)

            with open(src) as f:
                expected = f.read()
            with open(tgt) as f:
                result = f.read()

            self.assertEqual(result, expected)

    def test_copy_file_error(self):
        src = '/tmp/not-a-directory/src.txt'
        tgt = '/tmp/foobar/tgt.txt'
        with self.assertRaises(AssertionError):
            rpt.copy_file(src, tgt)

    def test_move_file(self):
        with TemporaryDirectory() as root:
            src = Path(root, 'src.txt')
            tgt = Path(root, 'target', 'tgt.txt')
            expected = 'foo\nbar'
            with open(src, 'w') as f:
                f.write(expected)
            rpt.move_file(src, tgt)

            with open(tgt) as f:
                result = f.read()

            self.assertEqual(result, expected)
            self.assertFalse(src.is_file())

    def test_move_file_error(self):
        src = '/tmp/not-a-directory/src.txt'
        tgt = '/tmp/foobar/tgt.txt'
        with self.assertRaises(AssertionError):
            rpt.move_file(src, tgt)
