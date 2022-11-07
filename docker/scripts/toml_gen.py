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

    args = parser.parse_args()
    text = generate_pyproject(args.template[0])
    print(text)


def generate_pyproject(template_file):
    # type: (str) -> str
    '''
    Generate pyproject.toml file given a template file.
    Removes dev dependecies.

    Args:
        template_file (str): Path to base pyproject.toml template file.

    Returns:
        str: pyproject.toml content.
    '''
    with open(template_file) as f:
        text = f.read()

    # remove arbitrary tag
    # if your project has a dependency that depends on an earlier version of
    # your project, you need to add an arbitrary tag to disrupt its namespace in
    # order for pdm to resolve
    text = re.sub('<drop>', '', text)

    # fix python version
    regex = '.*<replace>(.|\n)*</replace>'
    version = re.search(regex, text).group(0).split('\n')[1:-1]
    for line in version:
        if re.search('^#', line):
            version = line
            break
    version = re.sub('# *', '', version)
    text = re.sub(regex, version, text)

    # remove group section
    text = re.sub('\n.*<remove>(.|\n)*</remove>', '', text)

    # remove trailing newlines
    text = text.rstrip('\n')

    return text


if __name__ == '__main__':
    main()
