import os
import unittest

import rolling_pin.utils as utils
# ------------------------------------------------------------------------------


class UtilsTests(unittest.TestCase):
    def test_relative_path(self):
        result = utils.relative_path(__file__, '../../resources/foo.txt')
        self.assertTrue(os.path.exists(result))

    def test_is_standard_module(self):
        self.assertTrue(utils.is_standard_module('re'))
        self.assertTrue(utils.is_standard_module('math'))
        self.assertFalse(utils.is_standard_module('cv2'))
        self.assertFalse(utils.is_standard_module('pandas'))
