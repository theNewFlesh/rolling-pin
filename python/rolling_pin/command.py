import subprocess

import click
import lunchbox.theme as lbc

from rolling_pin.conform_etl import ConformETL
from rolling_pin.radon_etl import RadonETL
from rolling_pin.repo_etl import RepoETL
from rolling_pin.toml_etl import TomlETL
# ------------------------------------------------------------------------------

'''
Command line interface to rolling-pin library
'''

click.Context.formatter_class = lbc.ThemeFormatter


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
    {white}Copies source files to target filepaths according to given conform
    file.{clear}

    \b
    {cyan2}ARGUMENTS{clear}
        {cyan2}source{clear}  conform YAML filepath
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
    {white}Generate a dependency graph of a source repository and write it to a
    given filepath{clear}

    \b
    {cyan2}ARGUMENTS{clear}
        {cyan2}source{clear}  repository path
        {cyan2}target{clear}  target filepath
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
    {white}Write radon metrics plots of given repository to given filepath.
    {clear}

    \b
    {cyan2}ARGUMENTS{clear}
        {cyan2}source{clear}  repository path
        {cyan2}target{clear}  plot filepath
    '''
    RadonETL(source).write_plots(target)


@main.command()
@click.argument('source', type=str, nargs=1)
@click.argument('target', type=str, nargs=1)
def table(source, target):
    # type: (str, str) -> None
    '''
    {white}Write radon metrics tables of given repository to given directory
    {clear}

    \b
    {cyan2}ARGUMENTS{clear}
        {cyan2}source{clear}  repository path
        {cyan2}target{clear}  table directory
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
    {white}Generate a copy of a given TOML file with given edits indicated by
    flags. Flags are evalauted in the following order: edit, delete, search.
    Flags may be arbitrarily combined. Edit and delete flags may appear multiple
    times.{clear}

    \b
    {yellow2}EXAMPLES
        EXAMPLE-FILE------------------------------------------------------------{clear}
            {blue2}>>>{clear}cat example.toml{purple2}
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
        {yellow2}EDIT-FLAG-------------------------------------------------------------------{clear}
            {blue2}>>>{clear}rolling-pin toml foobar.toml --edit 'root.a=999'{purple2}
            [root]
            a = 999
            b = 2...
    \b
            {yellow2}--------------------------------------------------------------------{clear}
            {blue2}>>>{clear}rolling-pin toml foobar.toml \\
                   --edit 'root.a=[1, 2]'   \\
                   --edit 'root.b="xxx"'{purple2}
            [root]
            a = [
                1,
                2,
            ]
            b = "xxx"...
    \b
            {yellow2}--------------------------------------------------------------------{clear}
            {blue2}>>>{clear}rolling-pin toml foobar.toml --edit 'root.foo.bar="baz"'{purple2}
            ...
            hello = true
    \b
            [root.foo]
            bar = "baz"...

    \b
        {yellow2}DELETE-FLAG-------------------------------------------------------------{clear}
            {blue2}>>>{clear}rolling-pin toml foobar.toml \\
                   --delete 'root.foo.bar'  \\
                   --delete 'root.a'{purple2}
            [root]
            b = 2
    \b
            [world]
            hello = true

    \b
        {yellow2}SEARCH-FLAG-------------------------------------------------------------{clear}
            {blue2}>>>{clear}rolling-pin toml foobar.toml --search 'root.foo|world'{purple2}
            [world]
            hello = true
    \b
            [root.foo.bar]
            x = "y"

    \b
    {cyan2}ARGUMENTS{clear}
        {cyan2}source{clear}  TOML filepath
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
    {white}BASH completion code to be written to a _rolling-pin completion file.
    {clear}
    '''
    cmd = '_ROLLING_PIN_COMPLETE=bash_source rolling-pin'
    result = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    result.wait()
    click.echo(result.stdout.read())


@main.command()
def zsh_completion():
    '''
    {white}ZSH completion code to be written to a _rolling-pin completion file.
    {clear}
    '''
    cmd = '_ROLLING_PIN_COMPLETE=zsh_source rolling-pin'
    result = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    result.wait()
    click.echo(result.stdout.read())


if __name__ == '__main__':
    main()
