import unittest

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
