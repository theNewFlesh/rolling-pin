import os
import unittest

import rolling_pin.utils as utils
# ------------------------------------------------------------------------------


class UtilsTests(unittest.TestCase):
    def test_relative_path(self):
        result = utils.relative_path(__file__, '../../resources/foo.txt')
        self.assertTrue(os.path.exists(result))
