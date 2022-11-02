#!/usr/bin/env python3
from typing import List

from copy import deepcopy
import argparse
import re

import toml
# ------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description='Generates a pyproject.toml file for specific python version',
        usage='\ngenerate_pyproject [template] [python-version] [-h --help]'
    )

    parser.add_argument(
        'template',
        metavar='template',
        type=str,
        nargs=1,
        action='store',
        help='pyrpoject.toml filepath',
    )

    parser.add_argument(
        'version',
        metavar='version',
        type=str,
        nargs=1,
        action='store',
        help='python version',
    )

    parser.add_argument(
        '--groups',
        metavar='groups',
        type=str,
        nargs=1,
        default='all',
        action='store',
        help='python version',
    )

    args = parser.parse_args()
    temp, ver, grp = args.template[0], args.version[0], args.groups[0].split(',')
    text = generate_pyproject(temp, ver, grp)
    print(text)


def generate_pyproject(source_path, version, groups):
    # type: (str, str, List[str]) -> str
    '''
    Generate pyproject.toml file given a source_path and python version.
    Removes dev dependecies.

    Args:
        source_path (str): Path to base pyproject.toml file.
        target_path (str): Path to write generated pyproject.toml file.
        version (str): Python version.
        groups (list[str]): Dependency groups.

    Returns:
        str: pyproject.toml content.
    '''
    proj = toml.load(source_path)

    # remove arbitrary tag
    # if your project has a dependency that depends on an earlier version of
    # your project, you need to add an arbitrary tag to disrupt its namespace in
    # order for pdm to resolve
    proj['project']['name'] = re.sub('<.*>', '', proj['project']['name'])

    # fix python version
    proj['project']['requires-python'] = f'{version}'

    deps = deepcopy(proj['tool']['pdm']['dev-dependencies'])
    proj['tool']['pdm']['dev-dependencies'] = {}

    if groups == ['all']:
        groups = ['dev', 'test']
    for group in groups:
        if group in deps.keys():
            proj['tool']['pdm']['dev-dependencies'][group] = deps[group]

    return toml.dumps(proj)


if __name__ == '__main__':
    main()
