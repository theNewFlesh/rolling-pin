import json
import os
import unittest
from collections import OrderedDict
from pathlib import Path
from tempfile import TemporaryDirectory

import pydot
import pytest

import rolling_pin.tools as tools
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
    def test_try_(self):
        result = tools.try_(lambda x: int(x), 1.0, exception_value='bar')
        self.assertEqual(result, 1)

        result = tools.try_(lambda x: int(x), 'foo', exception_value='bar')
        self.assertEqual(result, 'bar')

        result = tools.try_(lambda x: int(x), 'foo')
        self.assertEqual(result, 'foo')

    def test_get_ordered_unique(self):
        x = [0, 0, 0, 1, 1, 2, 3, 4, 5, 5, 5]
        result = tools.get_ordered_unique(x)
        expected = [0, 1, 2, 3, 4, 5]
        self.assertEqual(result, expected)

    def test_is_iterable(self):
        self.assertTrue(tools.is_iterable({}))
        self.assertTrue(tools.is_iterable(OrderedDict({})))
        self.assertTrue(tools.is_iterable([]))
        self.assertTrue(tools.is_iterable(set()))
        self.assertTrue(tools.is_iterable(tuple()))

        self.assertTrue(tools.is_iterable([
            ('k0', 'v0'),
            ('k1', 'v1'),
        ]))
        self.assertFalse(tools.is_iterable(
            json.dumps({'a': 'b'})
        ))
        self.assertFalse(tools.is_iterable('foo'))

    # PREDICATE-FUNCTIONS-------------------------------------------------------
    def test_is_dictlike(self):
        self.assertTrue(tools.is_dictlike({}))
        self.assertTrue(tools.is_dictlike(OrderedDict({})))

        self.assertFalse(tools.is_dictlike(
            json.dumps({'a': 'b'})
        ))
        self.assertFalse(tools.is_dictlike([
            ('k0', 'v0'),
            ('k1', 'v1'),
        ]))
        self.assertFalse(tools.is_dictlike([]))
        self.assertFalse(tools.is_dictlike(set()))
        self.assertFalse(tools.is_dictlike(tuple()))
        self.assertFalse(tools.is_dictlike('foo'))

    def test_is_listlike(self):
        self.assertTrue(tools.is_listlike([]))
        self.assertTrue(tools.is_listlike(set()))
        self.assertTrue(tools.is_listlike(tuple()))
        self.assertTrue(tools.is_listlike([
            ('k0', 'v0'),
            ('k1', 'v1'),
        ]))

        self.assertFalse(tools.is_listlike({}))
        self.assertFalse(tools.is_listlike(OrderedDict({})))
        self.assertFalse(tools.is_listlike(
            json.dumps({'a': 'b'})
        ))
        self.assertFalse(tools.is_listlike('foo'))

    # FLATTEN-------------------------------------------------------------------
    def test_flatten_simple(self):
        data = self.get_simple_blob()
        expected = {
            'a0/b0/c0': 'a0/b0/c0/value',
            'a0/b0/c1': 'a0/b0/c1/value',
            'a0/b1/c0': 'a0/b1/c0/value',
        }
        result = tools.flatten(data)
        self.assertEqual(result, expected)

    def test_flatten_simple_separator(self):
        blob = self.get_simple_blob()
        expected = {
            'a0_b0_c0': 'a0/b0/c0/value',
            'a0_b0_c1': 'a0/b0/c1/value',
            'a0_b1_c0': 'a0/b1/c0/value',
        }
        result = tools.flatten(blob, separator='_')
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
        result = tools.flatten(blob, embed_types=True)
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
        result = tools.flatten(blob, separator='=>')
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
        result = tools.flatten(blob, embed_types=False)
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
        result = tools.flatten(blob, separator='=>', embed_types=False)
        self.assertEqual(result, expected)

    def test_flatten_double(self):
        expected = {
            'a0/b0/c0': 'a0/b0/c0/value',
            'a0/b0/c1': 'a0/b0/c1/value',
            'a0/b1/c0': 'a0/b1/c0/value',
        }
        result = tools.flatten(expected)
        result = tools.flatten(result)
        self.assertEqual(result, expected)

    # NEST----------------------------------------------------------------------
    def test_nest(self):
        blob = {
            'a0/b0/c0': 0,
            'a0/b1/c0': 1,
            'a0/b1/c1': 2,
        }
        expected = self.get_nested_dict()
        result = tools.nest(blob)
        self.assertEqual(result, expected)

        blob = {
            'foo': 0,
            'bar': 0,
            'foo/bar': 0,
        }
        expected = "Duplicate key conflict. Key: 'foo'."
        with self.assertRaisesRegex(KeyError, expected):
            tools.nest(blob)

    def test_nest_separator(self):
        blob = {
            'a0-b0-c0': 0,
            'a0-b1-c0': 1,
            'a0-b1-c1': 2,
        }
        expected = self.get_nested_dict()
        result = tools.nest(blob, separator='-')
        self.assertEqual(result, expected)

    def test_nest_double(self):
        expected = self.get_nested_dict()
        result = tools.nest(expected)
        result = tools.nest(result)
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
        result = tools.unembed(blob)
        self.assertEqual(result, expected)

    def test_unembed_nest_flatten_cycle(self):
        expected = self.get_complex_blob()
        result = tools.unembed(tools.nest(tools.flatten(expected)))
        result = tools.unembed(tools.nest(tools.flatten(result)))
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

            result = tools.list_all_files(root)
            expected = [
                Path(root, 'a0/m0.py'),
                Path(root, 'a1/m1.py'),
                Path(root, 'a1/b1/m2.py'),
                Path(root, 'a1/b1/m3.py'),
            ]
            for item in expected:
                self.assertIn(item, result)

    def test_get_parent_fields(self):
        result = tools.get_parent_fields('a/b/c/d')
        expected = ['a', 'a/b', 'a/b/c']
        self.assertEqual(result, expected)

        result = tools.get_parent_fields('a-b-c-d', separator='-')
        expected = ['a', 'a-b', 'a-b-c']
        self.assertEqual(result, expected)

    def test_dot_to_html(self):
        dot = pydot.Dot()
        with pytest.raises(ValueError) as e:
            tools.dot_to_html(dot, layout='foo')
        expected = 'Invalid layout value. foo not in '
        expected += "['circo', 'dot', 'fdp', 'neato', 'sfdp', 'twopi']."
        self.assertEqual(str(e.value), expected)

        tools.dot_to_html(dot)
        tools.dot_to_html(dot, as_png=True)

    def test_write_dot_graph(self):
        expected = 'Invalid extension found: bar. '
        expected += 'Valid extensions include: svg, dot, png.'
        with pytest.raises(ValueError) as e:
            tools.write_dot_graph(pydot.Dot(), '/tmp/foo.bar')
        self.assertEqual(str(e.value), expected)

        with TemporaryDirectory() as root:
            for ext in ['SVG', 'dot', 'pNg']:
                result = Path(root, 'foo.' + ext)
                tools.write_dot_graph(pydot.Dot(), result)
                self.assertTrue(os.path.exists(result))
