#!/usr/bin/env python3
from typing import Any, List

import argparse

import toml
# ------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description='Generate TOML content using a given TOML file',
        usage='\ntoml_gen [filepath] [-h --help]'
    )

    parser.add_argument(
        'filepath',
        metavar='filepath',
        type=str,
        nargs=1,
        action='store',
        help='TOML file',
    )

    parser.add_argument(
        '--replace',
        metavar='replace',
        type=str,
        nargs='+',
        default=[],
        action='append',
        help='replace key with value in comma separated pair',
    )

    parser.add_argument(
        '--delete',
        metavar='delete',
        type=str,
        nargs='+',
        default=[],
        action='append',
        help='key to be deleted',
    )

    args = parser.parse_args()
    filepath, repls, dels = args.filepath[0], args.replace, args.delete
    repls = [x[0].split(',') for x in repls]
    dels = [x[0] for x in dels]
    text = generate(filepath, repls, dels)
    print(text)


class PrettyEncoder(toml.TomlArraySeparatorEncoder):
    def __init__(self, _dict=dict, preserve=False, separator=','):
        super().__init__(_dict, preserve, ',\n   ')

    def dump_list(self, v):
        if len(v) == 0:
            return '[]'
        if len(v) == 1:
            return '["' + v[0] + '"]'
        output = super().dump_list(v)[1:-1].rstrip('    \n')
        return '[\n   ' + output + '\n]'


def generate(filepath, replacements, deletions):
    # type: (str, List[List[str, Any]], List[str]) -> str
    '''
    Generate TOML from a given TOML file and a list of replacements and
    deletions.

    Args:
        filepath (str): pyproject.toml filepath.
        replacements (List[List[str, object]]): LIst of key value pairs.
            Key is replaced with value.
        deletions (List[str]): Keys to be deleted.

    Returns:
        str: pyproject.toml content.
    '''
    data = toml.load(filepath)

    def lookup(key, data):
        keys = key.split('.')
        last_key = keys.pop()
        temp = data
        for k in keys:
            temp = temp[k]
        return temp, last_key

    for key, val in replacements:
        temp, k = lookup(key, data)
        temp[k]= val

    for key in deletions:
        temp, k = lookup(key, data)
        del temp[k]

    return toml.dumps(data, encoder=PrettyEncoder())


if __name__ == '__main__':
    main()
