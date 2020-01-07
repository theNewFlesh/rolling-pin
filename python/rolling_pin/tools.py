import logging
import os
import re
from collections import OrderedDict
from pathlib import Path

from IPython.display import HTML, Image

LOG_LEVEL = os.environ.get('LOG_LEVEL', 'WARNING').upper()
logging.basicConfig(level=LOG_LEVEL)
LOGGER = logging.getLogger(__name__)
# ------------------------------------------------------------------------------

'''
Contains basic functions for more complex ETL functions and classes.
'''

# COLOR-SCHEME------------------------------------------------------------------
COLOR_SCHEME = dict(
    background='#242424',
    node='#343434',
    node_font='#B6ECF3',
    node_value='#343434',
    node_value_font='#DE958E',
    edge='#B6ECF3',
    edge_value='#DE958E',
    node_library_font='#DE958E',
    node_subpackage_font='#A0D17B',
    node_module_font='#B6ECF3',
    edge_library='#DE958E',
    edge_subpackage='#A0D17B',
    edge_module='#B6ECF3',
)

COLOR_SCALE = [
    '#B6ECF3',
    '#DE958E',
    '#EBB483',
    '#A0D17B',
    '#93B6E6',
    '#AC92DE',
    '#E9EABE',
    '#7EC4CF',
    '#F77E70',
    '#EB9E58',
]


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
    '''
    Determines if given item is iterable.

    Args:
        item (object): Object to be tested.

    Returns:
        bool: Whether given item is iterable.
    '''
    if is_listlike(item) or is_dictlike(item):
        return True
    return False


def is_dictlike(item):
    '''
    Determines if given item is dict-like.

    Args:
        item (object): Object to be tested.

    Returns:
        bool: Whether given item is dict-like.
    '''
    for type_ in [dict, OrderedDict]:
        if isinstance(item, type_):
            return True
    return False


def is_listlike(item):
    '''
    Determines if given item is list-like.

    Args:
        item (object): Object to be tested.

    Returns:
        bool: Whether given item is list-like.
    '''
    for type_ in [list, tuple, set]:
        if isinstance(item, type_):
            return True
    return False


# CORE-FUNCTIONS----------------------------------------------------------------
def flatten(item, separator='/', embed_types=True):
    '''
    Flattens a iterable object into a flat dictionary.

    Args:
        item (object): Iterable object.
        separator (str, optional): Field separator in keys. Default: '/'.

    Returns:
        dict: Dictionary representation of given object.
    '''
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
                    final_key = re.sub('^' + separator, '', new_key)
                    output[final_key] = val

    recurse(item, '')
    return output


def nest(flat_dict, separator='/'):
    '''
    Converts a flat dictionary into a nested dictionary by splitting keys by a
    given separator.

    Args:
        flat_dict (dict): Flat dictionary.
        separator (str, optional): Field separator within given dictionary's
            keys. Default: '/'.

    Returns:
        dict: Nested dictionary.
    '''
    output = {}
    for keys, val in flat_dict.items():
        split_keys = list(filter(
            lambda x: x != '', keys.split(separator)
        ))
        cursor = output
        last = split_keys.pop()
        for key in split_keys:
            if key not in cursor:
                cursor[key] = {}

            if not isinstance(cursor[key], dict):
                msg = f"Duplicate key conflict. Key: '{key}'."
                raise KeyError(msg)

            cursor = cursor[key]
        cursor[last] = val
    return output


def unembed(item):
    '''
    Convert embeded types in dictionary keys into python types.

    Args:
        item (object): Dictionary with embedded types.

    Returns:
        object: Converted object.
    '''
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


# FILE-FUNCTIONS----------------------------------------------------------------
def list_all_files(directory):
    '''
    Recursively lists all files within a give directory.

    Args:
        directory (str or Path): Directory to be recursed.

    Returns:
        list[Path]: List of filepaths.
    '''
    output = []
    for root, dirs, files in os.walk(directory):
        for file_ in files:
            fullpath = Path(root, file_)
            output.append(fullpath)
    return output


def get_parent_fields(key, separator='/'):
    '''
    Get all the parent fields of a given key, split by given separator.

    Args:
        key (str): Key.
        separator (str, optional): String that splits key into fields.
            Default: '/'.

    Returns:
        list(str): List of absolute parent fields.
    '''
    fields = key.split(separator)
    output = []
    for i in range(len(fields) - 1):
        output.append(separator.join(fields[:i + 1]))
    return output


# EXPORT-FUNCTIONS--------------------------------------------------------------
def dot_to_html(dot, layout='dot', as_png=False):
    '''
    Converts a given pydot graph into a IPython.display.HTML object.
    Used in jupyter lab inline display of graph data.

    Args:
        dot (pydot.Dot): Pydot Graph instance.
        layout (str, optional): Graph layout style.
            Options include: circo, dot, fdp, neato, sfdp, twopi.
            Default: dot.
        as_png (bool, optional): Display graph as a PNG image instead of SVG.
            Useful for display on Github. Default: False.

    Raises:
        ValueError: If invalid layout given.

    Returns:
        IPython.display.HTML: HTML instance.
    '''
    layouts = ['circo', 'dot', 'fdp', 'neato', 'sfdp', 'twopi']
    if layout not in layouts:
        msg = f'Invalid layout value. {layout} not in {layouts}.'
        raise ValueError(msg)

    if as_png:
        return Image(data=dot.create_png())

    svg = dot.create_svg(prog=layout)
    html = f'<object type="image/svg+xml" data="data:image/svg+xml;{svg}"></object>'
    html = HTML(html)
    html.data = re.sub(r'\\n|\\', '', html.data)
    html.data = re.sub('</svg>.*', '</svg>', html.data)
    return html


def write_dot_graph(
    dot,
    fullpath,
    layout='dot',
):
    '''
    Writes a pydot.Dot object to a given filepath.
    Formats supported: svg, dot, png.

    Args:
        dot (pydot.Dot): Pydot Dot instance.
        fulllpath (str or Path): File to be written to.
        layout (str, optional): Graph layout style.
            Options include: circo, dot, fdp, neato, sfdp, twopi. Default: dot.

    Raises:
        ValueError: If invalid file extension given.
    '''
    if isinstance(fullpath, Path):
        fullpath = Path(fullpath).absolute().as_posix()

    _, ext = os.path.splitext(fullpath)
    ext = re.sub(r'^\.', '', ext)
    if re.search('^svg$', ext, re.I):
        dot.write_svg(fullpath, prog=layout)
    elif re.search('^dot$', ext, re.I):
        dot.write_dot(fullpath, prog=layout)
    elif re.search('^png$', ext, re.I):
        dot.write_png(fullpath, prog=layout)
    else:
        msg = f'Invalid extension found: {ext}. '
        msg += 'Valid extensions include: svg, dot, png.'
        raise ValueError(msg)
