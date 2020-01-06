import re
import os


def mod_func_2(filename):
    _, ext = os.path.splitext(filename)
    return re.sub('foo', ext, 'watermelon')


def cathat(dogfoot):
    return 'pigwig'
