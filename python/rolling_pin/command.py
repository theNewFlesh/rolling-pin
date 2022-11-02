import subprocess

import click

from rolling_pin.radon_etl import RadonETL
from rolling_pin.repo_etl import RepoETL
# ------------------------------------------------------------------------------

'''
Command line interface to rolling-pin library
'''


@click.group()
def main():
    pass  # pragma: no cover


@main.command()
@click.argument('source', type=str, nargs=1)
@click.argument('target', type=str, nargs=1)
@click.option(
    '--include',
    type=str,
    nargs=1,
    default=r'.*\.py$',
    help="include files that match this regex pattern. default: '.*\.py$'"
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
    if exclude == '':
        exclude = None
    RepoETL(source, include, exclude).write(target, orient=orient)


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
    cmd = '_ROLLING-PIN_COMPLETE=bash_source rolling_pin'  # pragma: no cover
    result = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)  # pragma: no cover
    result.wait()  # pragma: no cover
    click.echo(result.stdout.read())  # pragma: no cover


@main.command()
def zsh_completion():
    '''
        ZSH completion code to be written to a _rolling-pin completion file.
    '''
    cmd = '_ROLLING-PIN_COMPLETE=zsh_source rolling_pin'  # pragma: no cover
    result = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)  # pragma: no cover
    result.wait()  # pragma: no cover
    click.echo(result.stdout.read())  # pragma: no cover


if __name__ == '__main__':
    main()  # pragma: no cover
