import logging
import os
import re
from collections import OrderedDict
from pathlib import Path

from IPython.display import HTML

LOG_LEVEL = os.environ.get('LOG_LEVEL', 'WARNING').upper()
logging.basicConfig(level=LOG_LEVEL)
LOGGER = logging.getLogger(__name__)


# COLOR-SCHEME------------------------------------------------------------------
COLOR_SCHEME = dict(
    background='#242424',
    node='#343434',
    node_fontcolor='#B6ECF3',
    node_value='#343434',
    node_value_fontcolor='#DE958E',
    edge='#B6ECF3',
    edge_value_color='#DE958E',
    node_library_font='#DE958E',
    node_subpackage_font='#A0D17B',
    node_module_font='#B6ECF3',
    edge_library='#DE958E',
    edge_subpackage='#A0D17B',
    edge_module='#B6ECF3',
)


# ERRORS------------------------------------------------------------------------
class ValidationError(Exception):
    '''
    Error raised by all validators.
    '''
    pass


class EmptyError(Exception):
    '''
    Error raised when given object is empty.
    '''
    pass


# GENERAL-----------------------------------------------------------------------
def try_(function, item, exception_value='item'):
    '''
    Try applying a given function to a given item. If that fails return the item
    or exception value.

    Args:
        function (function): Function that expects an item.
        item (object): Item to be processed by function.
        exception_value (object, optional): If left to 'item', returns item, \
            else returns given value. Default: 'item'.

    Returns:
        object: Ouput of *function(item)* or exception_value.
    '''
    LOGGER.debug(f'try_ function called with: {item.__class__.__name__} object')
    try:
        return function(item)
    except Exception as e:
        LOGGER.debug(f'try_ function failed with message: {e}')
        if exception_value == 'item':
            return item
        return exception_value


def get_ordered_unique(items):
    '''
    Generates a unique list of items in same order they were received in.

    Args:
        items (list): List of items.

    Returns:
        list: Unique ordered list.
    '''
    output = []
    temp = set()
    for item in items:
        if item not in temp:
            output.append(item)
            temp.add(item)
    return output


# PREDICATE-FUNCTIONS-----------------------------------------------------------
def is_iterable(item):
    if is_listlike(item) or is_dictlike(item):
        return True
    return False


def is_dictlike(item):
    for type_ in [dict, OrderedDict]:
        if isinstance(item, type_):
            return True
    return False


def is_listlike(item):
    for type_ in [list, tuple, set]:
        if isinstance(item, type_):
            return True
    return False


# CORE-FUNCTIONS----------------------------------------------------------------
def flatten(item, separator='/', embed_types=True):
    output = {}

    def recurse(item, cursor):
        if is_listlike(item):
            if embed_types:
                name = item.__class__.__name__
                item = [(f'<{name}_{i}>', val) for i, val in enumerate(item)]
                item = dict(item)
            else:
                item = dict(enumerate(item))
        if is_dictlike(item):
            for key, val in item.items():
                new_key = f'{cursor}{separator}{str(key)}'
                if is_iterable(val) and len(val) > 0:
                    recurse(val, new_key)
                else:
                    output[new_key] = val

    recurse(item, '')
    return output


def nest(dict_, separator='/'):
    output = {}
    for keys, val in dict_.items():
        split_keys = list(filter(
            lambda x: x != '', keys.split(separator)
        ))
        cursor = output
        last = split_keys.pop()
        for key in split_keys:
            if key not in cursor:
                cursor[key] = {}
            cursor = cursor[key]
        cursor[last] = val
    return output


def unembed(item):
    lut = {'list': list, 'tuple': tuple, 'set': set}
    embed_re = re.compile(r'^<([a-z]+)_(\d+)>$')

    output = {}
    if is_dictlike(item) and item != {}:
        keys = list(item.keys())

        match = embed_re.match(keys[0])
        if match:
            indices = [embed_re.match(key).group(2) for key in keys]
            indices = map(int, indices)

            output = []
            for i, key in sorted(zip(indices, keys)):
                next_item = item[key]
                if is_dictlike(next_item):
                    next_item = unembed(next_item)
                output.append(next_item)

            output = lut[match.group(1)](output)
            return output
        else:
            for key, val in item.items():
                output[key] = unembed(val)
    else:
        output = item
    return output


def edit(dict_, regex, key_func=None, val_func=None):
    if key_func is None:
        key_func = lambda k: k
    if val_func is None:
        val_func = lambda v: v

    output = {}
    for key, val in dict_.items():
        if re.search(regex, key):
            output[key_func(key)] = val_func(val)
        else:
            output[key] = val
    return output


# FILE-FUNCTIONS----------------------------------------------------------------
def list_all_files(directory):
    output = []
    for root, dirs, files in os.walk(directory):
        for file_ in files:
            fullpath = Path(root, file_)
            output.append(fullpath)
    return output


def get_parents(item, separator='.'):
    items = item.split(separator)
    output = []
    for i in range(len(items) - 1):
        output.append(separator.join(items[:i + 1]))
    return output


def drop_duplicates(items):
    temp = set()
    output = []
    for item in items:
        if item not in temp:
            output.append(item)
            temp.add(item)
    return output


def get_imports(fullpath):
    with open(fullpath) as f:
        data = f.readlines()
    data = map(lambda x: x.strip('\n'), data)
    data = filter(lambda x: re.search('^import|^from', x), data)
    data = map(lambda x: re.sub('from (.*?) .*', '\\1', x), data)
    data = map(lambda x: re.sub(' as .*', '', x), data)
    data = map(lambda x: re.sub(' *#.*', '', x), data)
    data = map(lambda x: re.sub('import ', '', x), data)
    data = filter(lambda x: not is_builtin(x), data)
    return list(data)


def is_builtin(item):
    builtins = [
        'copy',
        'datetime',
        'enum',
        'functools',
        'inspect',
        'itertools',
        'json',
        'logging',
        'math',
        'os',
        'pathlib',
        're',
        'uuid'
    ]
    suffix = r'(\..*)?'
    builtins_re = f'{suffix}|'.join(builtins) + suffix
    if re.search(builtins_re, item):
        return True
    return False


# EXPORT-FUNCTIONS--------------------------------------------------------------
def dot_to_html(dot, layout='dot'):
    layouts = ['dot', 'twopi', 'circo', 'neato', 'fdp', 'sfdp']
    if layout not in layouts:
        msg = f'Invalid layout value. {layout} not in {layouts}.'
        raise ValueError(msg)

    svg = dot.create_svg(prog=layout)
    html = f'<img width="100%" src="data:image/svg+xml;{svg}" >'
    return HTML(html)


def write_dot_graph(
    graph,
    fullpath,
    layout='dot',
):
    if isinstance(fullpath, Path):
        fullpath = Path(fullpath).absolute().as_posix()

    _, ext = os.path.splitext(fullpath)
    if re.search(r'\.svg$', ext, re.I):
        graph.write_svg(fullpath, prog=layout)
    elif re.search(r'\.dot$', ext, re.I):
        graph.write_dot(fullpath, prog=layout)
    elif re.search(r'\.png$', ext, re.I):
        graph.write_png(fullpath, prog=layout)
    else:
        msg = f'Invalid extension found: {ext}. '
        msg += 'Valid extensions include: svg, dot, png.'
        raise ValueError(msg)
