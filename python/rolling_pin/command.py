import subprocess

import click

from rolling_pin.conform_etl import ConformETL
from rolling_pin.radon_etl import RadonETL
from rolling_pin.repo_etl import RepoETL
# ------------------------------------------------------------------------------

'''
Command line interface to rolling-pin library
'''


@click.group()
def main():
    pass


@main.command()
@click.argument('source', type=str, nargs=1)
@click.option(
    '--groups',
    type=str,
    nargs=1,
    default='all',
    help="Comma separated list of groups to be conformed. Default: 'all'"
)
@click.option(
    '--dryrun',
    is_flag=True,
    help="Print out conform table instead of run conform."
)
def conform(source, groups, dryrun):
    # type: (str, str, bool) -> None
    '''
    Copies source files to target filepaths according to given conform file.

    SOURCE - conform YAML filepath
    '''
    etl = ConformETL.from_yaml(source)
    if dryrun:
        print(etl)
    else:
        etl.conform(groups=groups.split(','))


@main.command()
@click.argument('source', type=str, nargs=1)
@click.argument('target', type=str, nargs=1)
@click.option(
    '--include',
    type=str,
    nargs=1,
    default=r'.*\.py$',
    help=r"include files that match this regex pattern. default: '.*\.py$'"
)
@click.option(
    '--exclude',
    type=str,
    nargs=1,
    default='test|mock',
    help="exclude files that match this regex pattern. default: 'test|mock'"
)
@click.option(
    '--orient', type=str, nargs=1, default='lr',
    help='graph orientation. default: lr.',
)
def graph(source, target, include, exclude, orient):
    # type: (str, str, str, str, str) -> None
    '''
    Generate a dependency graph of a source repository and write it to a given
    filepath

    SOURCE - repository path

    TARGET - target filepath
    '''
    include_ = None if include == '' else include
    exclude_ = None if exclude == '' else exclude
    RepoETL(source, include_, exclude_).write(target, orient=orient)


@main.command()
@click.argument('source', type=str, nargs=1)
@click.argument('target', type=str, nargs=1)
def plot(source, target):
    # type: (str, str) -> None
    '''
    Write radon metrics plots of given repository to given filepath

    SOURCE - repository path

    TARGET - plot filepath
    '''
    RadonETL(source).write_plots(target)


@main.command()
@click.argument('source', type=str, nargs=1)
@click.argument('target', type=str, nargs=1)
def table(source, target):
    # type: (str, str) -> None
    '''
    Write radon metrics tables of given repository to given directory

    SOURCE - repository path

    TARGET - table directory
    '''
    RadonETL(source).write_tables(target)


@main.command()
def bash_completion():
    '''
        BASH completion code to be written to a _rolling-pin completion file.
    '''
    cmd = '_ROLLING_PIN_COMPLETE=bash_source rolling-pin'
    result = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    result.wait()
    click.echo(result.stdout.read())


@main.command()
def zsh_completion():
    '''
        ZSH completion code to be written to a _rolling-pin completion file.
    '''
    cmd = '_ROLLING_PIN_COMPLETE=zsh_source rolling-pin'
    result = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    result.wait()
    click.echo(result.stdout.read())


if __name__ == '__main__':
    main()
