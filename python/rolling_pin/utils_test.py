import os
import unittest

import rolling_pin.utils as utils
# ------------------------------------------------------------------------------


@utils.api_function
def foobar_func(foo='<required>', bar='bar'):
    return foo + bar


class UtilsTests(unittest.TestCase):
    def test_relative_path(self):
        result = utils.relative_path(__file__, '../../resources/foo.txt')
        self.assertTrue(os.path.exists(result))

    def test_is_standard_module(self):
        self.assertTrue(utils.is_standard_module('re'))
        self.assertTrue(utils.is_standard_module('math'))
        self.assertFalse(utils.is_standard_module('cv2'))
        self.assertFalse(utils.is_standard_module('pandas'))

    def test_get_function_signature(self):
        def func(a, b, foo='bar', boo='baz'):
            pass
        result = utils.get_function_signature(func)
        expected = dict(
            args=['a', 'b'],
            kwargs=dict(foo='bar', boo='baz')
        )
        self.assertEqual(result, expected)

        def func(a, b):
            pass
        result = utils.get_function_signature(func)
        expected = dict(
            args=['a', 'b'],
            kwargs={},
        )
        self.assertEqual(result, expected)

        def func(foo='bar', boo='baz'):
            pass
        result = utils.get_function_signature(func)
        expected = dict(
            args=[],
            kwargs=dict(foo='bar', boo='baz')
        )
        self.assertEqual(result, expected)

        def func():
            pass
        result = utils.get_function_signature(func)
        expected = dict(
            args=[],
            kwargs={},
        )
        self.assertEqual(result, expected)

    def test_api_function(self):
        result = foobar_func(foo='taco', bar='cat')
        self.assertEqual(result, 'tacocat')

        result = foobar_func(foo='foo')
        self.assertEqual(result, 'foobar')

    def test_api_function_non_keyword(self):
        @utils.api_function
        def foobar_func(foo, bar='bar'):
            return foo + bar
        expected = 'Function may only have keyword arguments. '
        expected += r"Found non-keyword arguments: \['foo'\]."
        with self.assertRaisesRegex(TypeError, expected):
            foobar_func('foo', bar='bar')

    def test_api_function_no_keywords(self):
        @utils.api_function
        def foobar_func():
            return 'foobar'
        result = foobar_func()
        self.assertEqual(result, 'foobar')

        expected = r'foobar_func\(\) takes 0 positional arguments but 1 was given'
        with self.assertRaisesRegex(TypeError, expected):
            foobar_func('foo')

        expected = r"foobar_func\(\) got an unexpected keyword argument 'foo'"
        with self.assertRaisesRegex(TypeError, expected):
            foobar_func(foo='foo')

    def test_api_function_bad_keyword(self):
        expected = r"foobar_func\(\) got an unexpected keyword argument 'pizza'"
        with self.assertRaisesRegex(TypeError, expected):
            foobar_func(foo='foo', pizza='on a bagel')

    def test_api_function_required(self):
        expected = 'Missing required keyword argument: foo.'
        with self.assertRaisesRegex(ValueError, expected):
            foobar_func(bar='pumpkin')
