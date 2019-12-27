import json
import unittest
from collections import OrderedDict

import rolling_pin.tools as tools
# ------------------------------------------------------------------------------


class ToolsTests(unittest.TestCase):
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
