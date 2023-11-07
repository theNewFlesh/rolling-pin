import subprocess

import click

from rolling_pin.conform_etl import ConformETL
from rolling_pin.radon_etl import RadonETL
from rolling_pin.repo_etl import RepoETL
from rolling_pin.toml_etl import TomlETL
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

    \b
    Arguments:
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

    \b
    Arguments:
        SOURCE - repository path
        TARGET - target filepath
    '''
    include_ = '' if include is None else include
    exclude_ = '' if exclude is None else exclude
    RepoETL(source, include_, exclude_).write(target, orient=orient)


@main.command()
@click.argument('source', type=str, nargs=1)
@click.argument('target', type=str, nargs=1)
def plot(source, target):
    # type: (str, str) -> None
    '''
    Write radon metrics plots of given repository to given filepath

    \b
    Arguments:
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

    \b
    Arguments:
        SOURCE - repository path
        TARGET - table directory
    '''
    RadonETL(source).write_tables(target)


@main.command()
@click.argument('source', type=str, nargs=1)
@click.option(
    '--edit',
    type=str,
    nargs=1,
    multiple=True,
    help='''Replace key\'s value with given value. TEXT is "=" separated key
value pair in TOML format''',
)
@click.option(
    '--delete',
    type=str,
    nargs=1,
    multiple=True,
    help='Delete keys that match this regular expression',
)
@click.option(
    '--search',
    type=str,
    nargs=1,
    help='Search for keys that match this regular expression',
)
@click.option(
    '--target',
    type=str,
    nargs=1,
    help='Target filepath to write to',
)
def toml(source, edit, delete, search, target):
    # type: (str, tuple[str], tuple[str], str, str) -> None
    '''
    Generate a copy of a given TOML file with given edits indicated by flags.
    Flags are evalauted in the following order: edit, delete, search.
    Flags may be arbitrarily combined.
    Edit and delete flags may appear multiple times.

    \b
    Arguments:
        SOURCE - TOML filepath

    \b
    EXAMPLES
        EXAMPLE-FILE------------------------------------------------------------
            >>>cat example.toml
            [root]
            a = 1
            b = 2
    \b
            [root.foo.bar]
            x = "y"
    \b
            [world]
            hello = true

    \b
        EDIT-FLAG---------------------------------------------------------------
            >>>rolling-pin toml foobar.toml --edit 'root.a=999'
            [root]
            a = 999
            b = 2...
    \b
            --------------------------------------------------------------------
            >>>rolling-pin toml foobar.toml \\
                   --edit 'root.a=[1, 2]'   \\
                   --edit 'root.b="xxx"'
            [root]
            a = [
                1,
                2,
            ]
            b = "xxx"...
    \b
            --------------------------------------------------------------------
            >>>rolling-pin toml foobar.toml --edit 'root.foo.bar="baz"'
            ...
            hello = true
    \b
            [root.foo]
            bar = "baz"...

    \b
        DELETE-FLAG-------------------------------------------------------------
            >>>rolling-pin toml foobar.toml \\
                   --delete 'root.foo.bar'  \\
                   --delete 'root.a'
            [root]
            b = 2
    \b
            [world]
            hello = true

    \b
        SEARCH-FLAG-------------------------------------------------------------
            >>>rolling-pin toml foobar.toml --search 'root.foo|world'
            [world]
            hello = true
    \b
            [root.foo.bar]
            x = "y"
    '''
    etl = TomlETL.from_toml(source)
    for e in edit:
        etl = etl.edit(e)
    for d in delete:
        etl = etl.delete(d)
    if search is not None:
        etl = etl.search(search)
    if target is not None:
        etl.write(target)
    else:
        print(etl.to_string())


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
