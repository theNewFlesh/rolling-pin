import subprocess

import click

from  rolling_pin import repo_etl
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
    '--exclude', type=str, nargs=1, default='test|mock',
    help="exclude files that match this regex pattern. default: 'test|mock'"
)
@click.option(
    '--orient', type=str, nargs=1, default='lr',
    help='graph orientation. default: lr.',
)
def graph(source, target, exclude, orient):
    # type: (str, str, str, str) -> None
    '''
    Generate a dependency graph of a source repository and write it to a given
    target

    SOURCE - repository path

    TARGET - target filepath
    '''
    repo_etl.write_repo_architecture(source, target, exclude, orient)


@main.command()
@click.argument('source', type=str, nargs=1)
@click.argument('plot-path', type=str, nargs=1)
@click.argument('table-dir', type=str, nargs=1)
def plot(source, plot_path, table_dir):
    # type: (str, str, str) -> None
    '''
    Write repository plots and tables to given paths

    SOURCE    - repository path

    PLOT-PATH - plot filepath

    TABLE-DIR - table parent directory
    '''
    repo_etl.write_repo_plots_and_tables()


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
