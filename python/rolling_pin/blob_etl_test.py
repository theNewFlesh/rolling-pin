import os
import re
import unittest
from copy import deepcopy
from itertools import chain
from pathlib import Path
from tempfile import TemporaryDirectory

import IPython
import pytest

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

    def test_to_dict(self):
        expected = self.get_complex_blob()
        result = BlobETL(expected).to_dict()
        self.assertEqual(result, expected)

    def test_to_flat_dict(self):
        blob = self.get_complex_blob()
        expected = tools.flatten(blob, embed_types=True)
        result = BlobETL(blob).to_flat_dict()
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

        expected = r'Invalid by argument: foo\. Needs to be one of: '
        expected + r'key, value, key\+value\.'
        with self.assertRaisesRegex(ValueError, expected):
            etl.set(by='foo')

        k_set = lambda x: 'foo'
        v_set = lambda x: 'bar'
        expected = ['a0/b0/c0', 'a0/b1/c0', 'foo']

        result = etl.set(
            key_setter=k_set,
            value_setter=v_set,
            by='key'
        )._data
        self.assertEqual(result, {'foo': 'bar'})

        result = etl.set(
            lambda x: re.search('c1', x),
            k_set,
            v_set,
            by='key'
        )._data

        self.assertEqual(result['foo'], 'bar')
        result = sorted(list(result.keys()))
        self.assertEqual(result, expected)

        result = etl.set(
            lambda x: re.search('v1', x),
            k_set,
            v_set,
            by='value'
        )._data
        self.assertEqual(result['foo'], 'bar')
        result = sorted(list(result.keys()))
        self.assertEqual(result, expected)

        result = etl.set(
            lambda x, y: re.search('c1|v1', x + y),
            k_set,
            v_set,
            by='key+value'
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
                lambda x: re.search('bingo', x),
                key_setter=lambda x: re.sub('.*bingo', 'food', x)
            )\
            .set(
                lambda x: re.search('taco', x),
                value_setter=lambda x: 'salad'
            )\
            .set(
                lambda x: 'kiwi' in x,
                key_setter=lambda x: re.sub('kiwi', 'pepperoni', x)
            )\
            .delete(lambda x: x == 'v0', by='value')\
            .to_dict()
        print(result)
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