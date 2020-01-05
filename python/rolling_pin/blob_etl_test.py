from collections import deque
import os
import re
import unittest
from copy import deepcopy
from itertools import chain
from pathlib import Path
from tempfile import TemporaryDirectory

import IPython
import pytest
import numpy as np

import rolling_pin.tools as tools
from rolling_pin.blob_etl import BlobETL
# ------------------------------------------------------------------------------


class BlobEtlTests(unittest.TestCase):
    def get_simple_blob(self):
        data = {
            'a0': {
                'b0': {
                    'c0': 'v0',
                    'c1': 'v1',
                },
                'b1': {
                    'c0': 'v2',
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

    def test_init(self):
        blob = self.get_complex_blob()
        result = BlobETL(blob)._data
        self.assertEqual(
            result,
            tools.flatten(blob, embed_types=True)
        )

        sep = '~'
        blob = self.get_complex_blob()
        result = BlobETL(blob, separator=sep)._data
        self.assertEqual(
            result,
            tools.flatten(blob, separator=sep, embed_types=True)
        )

    def test_query(self):
        blob = self.get_complex_blob()
        expected = blob['a0']['b1'][1]['c3']
        expected = {'a0': {'b1': [{'c3': expected}]}}
        result = BlobETL(blob).query('.*c3').to_dict()
        self.assertEqual(result, expected)

        result = BlobETL(blob).query('.*C3', ignore_case=False).to_dict()
        self.assertEqual(result, {})

    def test_to_dict(self):
        expected = self.get_complex_blob()
        result = BlobETL(expected).to_dict()
        self.assertEqual(result, expected)

    def test_to_flat_dict(self):
        blob = self.get_complex_blob()
        expected = tools.flatten(blob, embed_types=True)
        result = BlobETL(blob).to_flat_dict()
        self.assertEqual(result, expected)

    def test_to_records(self):
        data = [
            {'a': {'b': 'c'}, 'd': 'e'},
            {'a': {'b': 'c'}, 'd': 'e'},
            {'a': {'b': 'c'}, 'd': 'e'},
        ]
        expected = [
            {0: '<list_0>', 1: 'a', 2: 'b', 'value': 'c'},
            {0: '<list_0>', 1: 'd', 'value': 'e'},
            {0: '<list_1>', 1: 'a', 2: 'b', 'value': 'c'},
            {0: '<list_1>', 1: 'd', 'value': 'e'},
            {0: '<list_2>', 1: 'a', 2: 'b', 'value': 'c'},
            {0: '<list_2>', 1: 'd', 'value': 'e'}
        ]
        result = BlobETL(data).to_records()
        self.assertEqual(result, expected)

    def test_to_dataframe(self):
        data = [
            {'a': {'b': 'c'}, 'd': 'e'},
            {'a': {'b': 'c'}, 'd': 'e'},
            {'a': {'b': 'c'}, 'd': 'e'},
        ]
        result = BlobETL(data).to_dataframe()
        expected = [
            ['<list_0>', 'a', 'b', 'c'],
            ['<list_0>', 'd', np.nan, 'e'],
            ['<list_1>', 'a', 'b', 'c'],
            ['<list_1>', 'd', np.nan, 'e'],
            ['<list_2>', 'a', 'b', 'c'],
            ['<list_2>', 'd', np.nan, 'e'],
        ]
        for i, row in enumerate(expected):
            self.assertEqual(result.loc[i].tolist(), row)

    def test_to_dataframe_group_by(self):
        data = {
            'l0_a': {
                'l1_a': {
                    'l2_a': 'v0',
                    'l2_b': 'v1',
                },
                'l1_b': {
                    'l2_c': 'v2',
                }
            },
            'l0_b': {
                'l1_c': 'v3'
            },
        }
        result = BlobETL(data).to_dataframe(group_by=2)
        expected = [
            {0: 'l0_a', 1: 'l1_a', 2: ['l2_a', 'l2_b'], 'value': ['v0', 'v1']},
            {0: 'l0_a', 1: 'l1_b', 2: ['l2_c'], 'value': ['v2']},
            {0: 'l0_b', 1: 'l1_c', 2: [np.nan], 'value': ['v3']},
        ]
        for i, row in enumerate(expected):
            self.assertEqual(result.loc[i].to_dict(), row)

        result = BlobETL(data).to_dataframe(group_by=1)
        expected = [
            {
                0: 'l0_a',
                1: ['l1_a', 'l1_a', 'l1_b'],
                2: ['l2_a', 'l2_b', 'l2_c'],
                'value': ['v0', 'v1', 'v2'],
            },
            {0: 'l0_b', 1: ['l1_c'], 2: [np.nan], 'value': ['v3']},
        ]
        for i, row in enumerate(expected):
            self.assertEqual(result.loc[i].to_dict(), row)

    def test_to_prototype(self):
        data = {
            'users': [
                {'name': {'first': 'tom', 'last': 'smith'}},
                {'name': {'first': 'dick', 'last': 'smith'}},
                {'name': {'first': 'jane', 'last': 'doe'}},
            ]
        }
        expected = {
            '^users': {
                '<list_[0-9]+>': {
                    'name': {
                        'first$': ['dick', 'jane', 'tom'],
                        'last$': ['doe', 'smith']
                    }
                }
            }
        }
        result = BlobETL(data).to_prototype().to_dict()
        self.assertEqual(result, expected)

    def test_to_prototype_no_hashable_values(self):
        unhashable = deque()

        data = {
            'users': [
                {
                    'name': {'first': 'tom', 'last': 'smith'},
                    'unhashable': unhashable,
                },
                {
                    'name': {'first': 'dick', 'last': 'smith'},
                    'unhashable': unhashable,
                },
                {
                    'name': {'first': 'jane', 'last': 'doe'},
                    'unhashable': unhashable,
                },
            ]
        }
        expected = {
            '^users': {
                '<list_[0-9]+>': {
                    'name': {
                        'first$': ['dick', 'jane', 'tom'],
                        'last$': ['doe', 'smith']
                    },
                    'unhashable$': [unhashable, unhashable, unhashable],
                }
            }
        }
        result = BlobETL(data).to_prototype().to_dict()
        self.assertEqual(result, expected)

    def test_filter(self):
        blob = self.get_simple_blob()
        etl = BlobETL(blob)

        expected = r'Invalid by argument: foo\. Needs to be one of: '
        expected + r'key, value, key\+value\.'
        with self.assertRaisesRegex(ValueError, expected):
            etl.filter(lambda x: x, by='foo')

        result = etl.filter(lambda x: re.search('c1', x), by='key')._data
        expected = {'a0/b0/c1': 'v1'}
        self.assertEqual(result, expected)

        result = etl.filter(lambda x: re.search('v1', x), by='value')._data
        self.assertEqual(result, expected)

        result = etl.filter(
            lambda x, y: re.search('c1|v1', x + y), by='key+value'
        )._data
        self.assertEqual(result, expected)

        result = etl\
            .filter(lambda x: re.search('b0', x), by='key')\
            .filter(lambda x: x == 'v0', by='value')\
            ._data
        expected = {'a0/b0/c0': 'v0'}
        self.assertEqual(result, expected)

    def test_delete(self):
        blob = self.get_simple_blob()
        etl = BlobETL(blob)

        expected = r'Invalid by argument: foo\. Needs to be one of: '
        expected + r'key, value, key\+value\.'
        with self.assertRaisesRegex(ValueError, expected):
            etl.delete(lambda x: x, by='foo')

        result = etl.delete(lambda x: re.search('c1', x), by='key')._data
        expected = tools.flatten(deepcopy(blob))
        del expected['a0/b0/c1']
        self.assertEqual(result, expected)

        result = etl.delete(lambda x: re.search('v1', x), by='value')._data
        self.assertEqual(result, expected)

        result = etl.delete(
            lambda x, y: re.search('c1|v1', x + y), by='key+value'
        )._data
        self.assertEqual(result, expected)

        result = etl\
            .delete(lambda x: re.search('b0', x), by='key')\
            .delete(lambda x: x == 'v1', by='value')\
            ._data
        expected = tools.flatten(deepcopy(blob))
        del expected['a0/b0/c0']
        del expected['a0/b0/c1']
        self.assertEqual(result, expected)

    def test_set(self):
        blob = self.get_simple_blob()
        etl = BlobETL(blob)

        k_set = lambda k, v: 'foo'
        v_set = lambda k, v: 'bar'
        expected = ['a0/b0/c0', 'a0/b1/c0', 'foo']

        result = etl.set(
            key_setter=k_set,
            value_setter=v_set,
        )._data
        self.assertEqual(result, {'foo': 'bar'})

        result = etl.set(
            lambda k, v: re.search('c1', k),
            k_set,
            v_set,
        )._data

        self.assertEqual(result['foo'], 'bar')
        result = sorted(list(result.keys()))
        self.assertEqual(result, expected)

        result = etl.set(
            lambda k, v: re.search('v1', v),
            k_set,
            v_set,
        )._data
        self.assertEqual(result['foo'], 'bar')
        result = sorted(list(result.keys()))
        self.assertEqual(result, expected)

        result = etl.set(
            lambda x, y: re.search('c1|v1', x + y),
            k_set,
            v_set,
        )._data
        self.assertEqual(result['foo'], 'bar')
        result = sorted(list(result.keys()))
        self.assertEqual(result, expected)

    def test_update(self):
        blob = self.get_simple_blob()
        etl = BlobETL(blob)

        temp = {
            'foo': {
                'bar': 'baz',
                'bingo': [
                    {'bango': 'bongo'}
                ]
            }
        }
        result = etl.update(temp)._data
        self.assertEqual(result['foo/bar'], 'baz')
        self.assertEqual(result['foo/bingo/<list_0>/bango'], 'bongo')

    def test_set_field(self):
        data = {
            'a/foo/c': 0,
            'a/b/c/d': 0,
        }
        etl = BlobETL(data)
        with self.assertRaises(IndexError):
            etl.set_field(3, lambda x: 'foo')._data

        result = etl.set_field(
            1,
            lambda x: 'bar' if x == 'foo' else x
        )._data
        expected = {
            'a/bar/c': 0,
            'a/b/c/d': 0,
        }

        result = etl.set_field(
            1,
            lambda x: 'foo'
        )._data
        expected = {
            'a/foo/c': 0,
            'a/foo/c/d': 0,
        }
        self.assertEqual(result, expected)

    def test_filter_delete_update_set(self):
        blob = self.get_simple_blob()
        etl = BlobETL(blob)

        temp = {
            'a0': {
                'b1': {
                    'bar': 'baz',
                    'bingo': [
                        {'bango': 'bongo'},
                        {'taco': 'cat'},
                        {'kiwi': 'pizza'},
                    ]
                }
            }
        }
        a = etl\
            .update(temp)\
            .filter(lambda x: x in ['pizza', 'cat'], by='value')
        b = etl\
            .filter(lambda x: re.search('b0', x), by='key')
        result = a\
            .update(b)\
            .set(
                lambda k, v: re.search('bingo', k),
                key_setter=lambda k, v: re.sub('.*bingo', 'food', k)
            )\
            .set(
                lambda k, v: re.search('taco', k),
                value_setter=lambda k, v: 'salad'
            )\
            .set(
                lambda k, v: 'kiwi' in k,
                key_setter=lambda k, v: re.sub('kiwi', 'pepperoni', k)
            )\
            .delete(lambda x: x == 'v0', by='value')\
            .to_dict()

        self.assertEqual(result['a0']['b0']['c1'], 'v1')
        self.assertEqual(result['food'][0]['taco'], 'salad')
        self.assertEqual(result['food'][1]['pepperoni'], 'pizza')

    def test_to_networkx_graph(self):
        blob = self.get_simple_blob()
        etl = BlobETL(blob)
        result = etl.to_networkx_graph()

        nodes = [
            ['root/a0', 'root/a0/b0', 'root/a0/b0/c0', '"root/a0/b0/c0/v0"'],
            ['root/a0', 'root/a0/b0', 'root/a0/b0/c1', '"root/a0/b0/c1/v1"'],
            ['root/a0', 'root/a0/b1', 'root/a0/b1/c0', '"root/a0/b1/c0/v2"'],
        ]
        edges = []
        for row in nodes:
            edges.append((row[0], row[1]))
            edges.append((row[1], row[2]))
            edges.append((row[2], row[3]))
        nodes = chain(*nodes)

        for node in nodes:
            self.assertTrue(result.has_node(node))

        for edge in edges:
            self.assertTrue(result.has_edge(*edge))

        self.assertEqual(result.number_of_nodes(), 6 + 3)
        self.assertEqual(result.number_of_edges(), 5 + 3)

        self.assertEqual(result.nodes['root/a0/b0/c0']['value'][0], 'v0')

    def test_to_dot_graph_error(self):
        blob = self.get_simple_blob()
        with pytest.raises(ValueError) as e: 
            BlobETL(blob).to_dot_graph(orient='foo')
        expected = "Invalid orient value. foo not in ['tb', 'bt', 'lr', 'rl']."
        self.assertEqual(str(e.value), expected)

    def test_to_dot_graph(self):
        color_scheme = dict(
            background='#000000',
            node='#AAAAAA',
            node_font='#BBBBBB',
            node_value='#CCCCCC',
            node_value_font='#DDDDDD',
            edge='#EEEEEE',
            edge_value='#FFFFFF',
        )

        blob = self.get_simple_blob()
        etl = BlobETL(blob)

        result = etl.to_dot_graph(orthogonal_edges=True)
        self.assertEqual(result.get_splines(), 'ortho')

        result = etl.to_dot_graph(color_scheme=color_scheme)
        self.assertEqual(result.get_bgcolor(), color_scheme['background'])

        for node in result.get_nodes():
            attrs = node.get_attributes()
            if attrs['node_type'] == 'key':
                self.assertEqual(node.get_color(), color_scheme['node'])
                self.assertEqual(node.get_fillcolor(), color_scheme['node'])
                self.assertEqual(node.get_fontcolor(), color_scheme['node_font'])
            if attrs['node_type'] == 'value':
                self.assertEqual(node.get_color(), color_scheme['node_value'])
                self.assertEqual(node.get_fillcolor(), color_scheme['node_value'])
                self.assertEqual(node.get_fontcolor(), color_scheme['node_value_font'])

        for edge in result.get_edges():
            node = result.get_node(edge.get_destination())[0]
            attrs = node.get_attributes()
            if attrs['node_type'] == 'key':
                self.assertEqual(edge.get_color(), color_scheme['edge'])
            if attrs['node_type'] == 'value':
                self.assertEqual(edge.get_color(), color_scheme['edge_value'])

    def test_to_html(self):
        blob = self.get_simple_blob()
        etl = BlobETL(blob)
        result = etl.to_html()
        self.assertIsInstance(result, IPython.display.HTML)

    def test_write(self):
        with TemporaryDirectory() as root:
            blob = self.get_simple_blob()
            etl = BlobETL(blob)

            result = Path(root, 'foo.svg')
            etl.write(result)
            self.assertTrue(os.path.exists(result))

            result = Path(root, 'foo.dot')
            etl.write(result)
            self.assertTrue(os.path.exists(result))

            result = Path(root, 'foo.png')
            etl.write(result)
            self.assertTrue(os.path.exists(result))

            result = Path(root, 'foo.json').absolute().as_posix()
            etl.write(result)
            self.assertTrue(os.path.exists(result))

            with pytest.raises(ValueError) as e:
                etl.write(Path(root, 'foo.bar'))
            expected = 'Invalid extension found: bar. Valid extensions '
            expected += 'include: svg, dot, png, json.'
            self.assertEqual(str(e.value), expected)
