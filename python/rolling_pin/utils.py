import logging
import os
from itertools import dropwhile, takewhile
from pathlib import Path

LOG_LEVEL = os.environ.get('LOG_LEVEL', 'WARNING').upper()
logging.basicConfig(level=LOG_LEVEL)
LOGGER = logging.getLogger(__name__)
# ------------------------------------------------------------------------------


def relative_path(module, path):
    '''
    Resolve path given current module's file path and given suffix.

    Args:
        module (str): Always __file__ of current module.
        path (str): Path relative to __file__.

    Returns:
        Path: Resolved Path object.
    '''
    module_root = Path(module).parent
    path = Path(path).parts
    path = list(dropwhile(lambda x: x == ".", path))
    up = len(list(takewhile(lambda x: x == "..", path)))
    path = Path(*path[up:])
    root = list(module_root.parents)[up - 1]
    output = Path(root, path).absolute()

    LOGGER.debug(
        f'relative_path called with: {module} and {path}. Returned: {output}')
    return output
