#!/usr/bin/env python3

import argparse

from rolling_pin.conform_etl import ConformETL
# ------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description='Executes rolling_pin conform on a conform file.',
        usage='\nrolling-pin [filepath] [groups] [-h --help]'
    )

    parser.add_argument(
        'filepath',
        metavar='filepath',
        type=str,
        nargs=1,
        action='store',
        help='conform yaml',
    )

    parser.add_argument(
        '--groups',
        metavar='groups',
        type=str,
        nargs=1,
        action='store',
        help='groups',
        default=['all'],
    )
    args = parser.parse_args()
    filepath = args.filepath[0]
    groups = args.groups[0].split(',')
    if groups == ['all']:
        groups = 'all'
    ConformETL.from_yaml(filepath).conform(groups)

if __name__ == '__main__':
    main()
