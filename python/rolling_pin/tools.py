from typing import Any, Dict, Generator, Iterable, List, Optional, Union  # noqa: F401
import pydot  # noqa: F401

from collections import OrderedDict
from pathlib import Path
import logging
import os
import re
import shutil

from IPython.display import HTML, Image
import pandas as pd

Filepath = Union[str, Path]
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
)  # type: Dict[str, str]


PLOTLY_COLOR_SCHEME = dict(
    bg='#242424',
    blue1='#5F95DE',
    blue2='#93B6E6',
    cyan1='#7EC4CF',
    cyan2='#B6ECF3',
    dark1='#040404',
    dark2='#141414',
    dialog1='#444459',
    dialog2='#5D5D7A',
    green1='#8BD155',
    green2='#A0D17B',
    grey1='#343434',
    grey2='#444444',
    light1='#A4A4A4',
    light2='#F4F4F4',
    orange1='#EB9E58',
    orange2='#EBB483',
    purple1='#C98FDE',
    purple2='#AC92DE',
    red1='#F77E70',
    red2='#DE958E',
    yellow1='#E8EA7E',
    yellow2='#E9EABE',
)


COLOR_SCALE = [
    'cyan2', 'red2', 'green2', 'blue2', 'orange2', 'purple2', 'yellow2',
    'light2', 'cyan1', 'red1', 'green1', 'blue1'
]  # type: List[str]
COLOR_SCALE = [PLOTLY_COLOR_SCHEME[x] for x in COLOR_SCALE]


PLOTLY_LAYOUT_THEME = {
    'legend': {
        'bgcolor': PLOTLY_COLOR_SCHEME['bg'],
        'title': {'text': ''},
        'font': {
            'color': PLOTLY_COLOR_SCHEME['light2']
        }
    },
    'paper_bgcolor': PLOTLY_COLOR_SCHEME['bg'],
    'plot_bgcolor': PLOTLY_COLOR_SCHEME['bg'],
    'title': {
        'font': {
            'color': PLOTLY_COLOR_SCHEME['light2']
        }
    },
    'xaxis': {
        'gridcolor': PLOTLY_COLOR_SCHEME['grey1'],
        'showgrid': True,
        'tickfont': {
            'color': PLOTLY_COLOR_SCHEME['light1']
        },
        'title': {
            'font': {
                'color': PLOTLY_COLOR_SCHEME['light1']
            }
        },
        'zerolinecolor': PLOTLY_COLOR_SCHEME['grey2']
    },
    'yaxis': {
        'gridcolor': PLOTLY_COLOR_SCHEME['grey1'],
        'showgrid': True,
        'tickfont': {
            'color': PLOTLY_COLOR_SCHEME['light1']
        },
        'title': {
            'font': {
                'color': PLOTLY_COLOR_SCHEME['light1']
            }
        },
        'zerolinecolor': PLOTLY_COLOR_SCHEME['grey2']
    }
}


# PREDICATE-FUNCTIONS-----------------------------------------------------------
def is_iterable(item):
    # type: (Any) -> bool
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
    # type: (Any) -> bool
    '''
    Determines if given item is dict-like.

    Args:
        item (object): Object to be tested.

    Returns:
        bool: Whether given item is dict-like.
    '''
    for type_ in [dict, OrderedDict]:
        if isinstance(item, type_):
            if item.__class__.__name__ == 'Counter':
                return False
            return True
    return False


def is_listlike(item):
    # type: (Any) -> bool
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
    # type: (Iterable, str, bool) -> Dict[str, Any]
    '''
    Flattens a iterable object into a flat dictionary.

    Args:
        item (object): Iterable object.
        separator (str, optional): Field separator in keys. Default: '/'.

    Returns:
        dict: Dictionary representation of given object.
    '''
    output = {}  # type: Dict[str, Any]

    def recurse(item, cursor):
        # type (Iterable, Any) -> None
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
    # type: (Dict[str, Any], str) -> Dict[str, Any]
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
    output = {}  # type: Dict[str, Any]
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
    # type: (Any) -> Any
    '''
    Convert embeded types in dictionary keys into python types.

    Args:
        item (object): Dictionary with embedded types.

    Returns:
        object: Converted object.
    '''
    lut = {'list': list, 'tuple': tuple, 'set': set}
    embed_re = re.compile(r'^<([a-z]+)_(\d+)>$')

    if is_dictlike(item) and item != {}:
        output = {}  # type: Any
        keys = list(item.keys())
        match = embed_re.match(keys[0])
        if match:
            indices = [embed_re.match(key).group(2) for key in keys]  # type: ignore
            indices = map(int, indices)  # type: ignore

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
        return output
    return item


# FILE-FUNCTIONS----------------------------------------------------------------
def list_all_files(
    directory,           # type: Filepath
    include_regex=None,  # type: Optional[str]
    exclude_regex=None   # type: Optional[str]
):
    # type: (...) -> Generator[Path, None, None]
    '''
    Recusively list all files within a given directory.

    Args:
        directory (str or Path): Directory to walk.
        include_regex (str, optional): Include filenames that match this regex.
            Default: None.
        exclude_regex (str, optional): Exclude filenames that match this regex.
            Default: None.

    Raises:
        FileNotFoundError: If argument is not a directory or does not exist.

    Yields:
        Path: File.
    '''
    directory = Path(directory)
    if not directory.is_dir():
        msg = f'{directory} is not a directory or does not exist.'
        raise FileNotFoundError(msg)

    include_re = re.compile(include_regex or '')  # type: Any
    exclude_re = re.compile(exclude_regex or '')  # type: Any

    for root, _, files in os.walk(directory):
        for file_ in files:
            filepath = Path(root, file_)

            output = True
            temp = filepath.absolute().as_posix()
            if include_regex is not None and not include_re.search(temp):
                output = False
            if exclude_regex is not None and exclude_re.search(temp):
                output = False

            if output:
                yield Path(root, file_)


def directory_to_dataframe(directory, include_regex='', exclude_regex=r'\.DS_Store'):
    # type: (Filepath, str, str) -> pd.DataFrame
    r'''
    Recursively list files with in a given directory as rows in a pd.DataFrame.

    Args:
        directory (str or Path): Directory to walk.
        include_regex (str, optional): Include filenames that match this regex.
            Default: None.
        exclude_regex (str, optional): Exclude filenames that match this regex.
            Default: '\.DS_Store'.

    Returns:
        pd.DataFrame: pd.DataFrame with one file per row.
    '''
    files = list_all_files(
        directory,
        include_regex=include_regex,
        exclude_regex=exclude_regex
    )  # type: Any
    files = sorted(list(files))

    data = pd.DataFrame()
    data['filepath'] = files
    data['filename'] = data.filepath.apply(lambda x: x.name)
    data['extension'] = data.filepath \
        .apply(lambda x: Path(x).suffix.lstrip('.'))
    data.filepath = data.filepath.apply(lambda x: x.absolute().as_posix())
    return data


def get_parent_fields(key, separator='/'):
    # type: (str, str) -> List[str]
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
    output = []  # type: List[str]
    for i in range(len(fields) - 1):
        output.append(separator.join(fields[:i + 1]))
    return output


def filter_text(
    text,                # type: str
    include_regex=None,  # type: Optional[str]
    exclude_regex=None,  # type: Optional[str]
    replace_regex=None,  # type: Optional[str]
    replace_value=None,  # type: Optional[str]
):
    # type: (...) -> str
    '''
    Filter given text by applying regular expressions to each line.

    Args:
        text (str): Newline separated lines.
        include_regex (str, optional): Keep lines that match given regex.
            Default: None.
        exclude_regex (str, optional): Remove lines that match given regex.
            Default: None.
        replace_regex (str, optional): Substitutes regex matches in lines with
            replace_value. Default: None.
        replace_value (str, optional): Regex substitution value. Default: ''.

    Raises:
        AssertionError: If source is not a file.

    Returns:
        str: Filtered text.
    '''
    lines = text.split('\n')
    if include_regex is not None:
        lines = list(filter(lambda x: re.search(include_regex, x), lines))
    if exclude_regex is not None:
        lines = list(filter(lambda x: not re.search(exclude_regex, x), lines))
    if replace_regex is not None:
        rep_val = replace_value or ''
        lines = [re.sub(replace_regex, rep_val, x) for x in lines]
    output = '\n'.join(lines)
    return output


def read_text(filepath):
    # type: (Filepath) -> str
    '''
    Convenience function for reading text from given file.

    Args:
        filepath (str or Path): File to be read.

    Raises:
        AssertionError: If source is not a file.

    Returns:
        str: text.
    '''
    assert Path(filepath).is_file()
    with open(filepath) as f:
        return f.read()


def write_text(text, filepath):
    # type: (str, Filepath) -> None
    '''
    Convenience function for writing text to given file.
    Creates directories as needed.

    Args:
        text (str): Text to be written.
        filepath (str or Path): File to be written.
    '''
    os.makedirs(Path(filepath).parent, exist_ok=True)
    with open(filepath, 'w') as f:
        f.write(text)


def copy_file(source, target):
    # type: (Filepath, Filepath) -> None
    '''
    Copy a source file to a target file. Creating directories as needed.

    Args:
        source (str or Path): Source filepath.
        target (str or Path): Target filepath.

    Raises:
        AssertionError: If source is not a file.
    '''
    assert Path(source).is_file()
    os.makedirs(Path(target).parent, exist_ok=True)
    shutil.copy2(source, target)


def move_file(source, target):
    # type: (Filepath, Filepath) -> None
    '''
    Moves a source file to a target file. Creating directories as needed.

    Args:
        source (str or Path): Source filepath.
        target (str or Path): Target filepath.

    Raises:
        AssertionError: If source is not a file.
    '''
    src = Path(source).as_posix()
    assert Path(src).is_file()
    os.makedirs(Path(target).parent, exist_ok=True)
    shutil.move(src, target)


# EXPORT-FUNCTIONS--------------------------------------------------------------
def dot_to_html(dot, layout='dot', as_png=False):
    # type: (pydot.Dot, str, bool) -> Union[HTML, Image]
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
    html = f'<object type="image/svg+xml" data="data:image/svg+xml;{svg}"></object>'  # type: Any
    html = HTML(html)
    html.data = re.sub(r'\\n|\\', '', html.data)
    html.data = re.sub('</svg>.*', '</svg>', html.data)
    return html


def write_dot_graph(
    dot,
    fullpath,
    layout='dot',
):
    # type: (pydot.Dot, Union[str, Path], str) -> None
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


# MISC-FUNCTIONS----------------------------------------------------------------
def replace_and_format(regex, replace, string, flags=0):
    # type: (str, str, str, Any) -> str
    r'''
    Perform a regex substitution on a given string and format any named group
    found in the result with groupdict data from the pattern. Group beggining
    with 'i' will be converted to integers. Groups beggining with 'f' will be
    converted to floats.

    ----------------------------------------------------------------------------

    Named group anatomy:
    ====================
        * (?P<NAME>PATTERN)
        * NAME becomes a key and whatever matches PATTERN becomes its value.
        >>> re.search('(?P<i>\d+)', 'foobar123').groupdict()
        {'i': '123'}

    ----------------------------------------------------------------------------

    Examples:
    =========
        Special groups:
            * (?P<i>\d)     - string matched by '\d' will be converted to an integer
            * (?P<f>\d)     - string matched by '\d' will be converted to an float
            * (?P<i_foo>\d) - string matched by '\d' will be converted to an integer
            * (?P<f_bar>\d) - string matched by '\d' will be converted to an float

        Named groups (long):
            >>> proj = '(?P<p>[a-z0-9]+)'
            >>> spec = '(?P<s>[a-z0-9]+)'
            >>> desc = '(?P<d>[a-z0-9\-]+)'
            >>> ver = '(?P<iv>\d+)\.'
            >>> frame = '(?P<i_f>\d+)'
            >>> regex = f'{proj}\.{spec}\.{desc}\.v{ver}\.{frame}.*'
            >>> replace = 'p-{p}_s-{s}_d-{d}_v{iv:03d}_f{i_f:04d}.jpeg'
            >>> string = 'proj.spec.desc.v1.25.png'
            >>> replace_and_format(regex, replace, string, flags=re.IGNORECASE)
            p-proj_s-spec_d-desc_v001_f0025.jpeg

        Named groups (short):
            >>> replace_and_format(
                '(?P<p>[a-z0-9]+)\.(?P<s>[a-z0-9]+)\.(?P<d>[a-z0-9\-]+)\.v(?P<iv>\d+)\.(?P<i_f>\d+).*',
                'p-{p}_s-{s}_d-{d}_v{iv:03d}_f{i_f:04d}.jpeg',
                'proj.spec.desc.v1.25.png',
            )
            p-proj_s-spec_d-desc_v001_f0025.jpeg

        No groups:
            >>> replace_and_format('foo', 'bar', 'foobar')
            barbar

    ----------------------------------------------------------------------------

    Args:
        regex (str): Regex pattern to search string with.
        replace (str): Replacement string which may contain formart variables
            ie '{variable}'.
        string (str): String to be converted.
        flags (object, optional): re.sub flags. Default: 0.

    Returns:
        str: Converted string.
    '''
    match = re.search(regex, string, flags=flags)
    grp = {}
    if match:
        grp = match.groupdict()

    for key, val in grp.items():
        if key.startswith('f'):
            grp[key] = float(val)
        elif key.startswith('i'):
            grp[key] = int(val)

    output = re.sub(regex, replace, string, flags=flags)
    # .format won't evaluate math expressions so do this
    if grp != {}:
        output = eval(f"f'{output}'", None, grp)
    return output
