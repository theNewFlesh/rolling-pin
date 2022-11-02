import subprocess

import click

import lunchbox.tools as lbt
# ------------------------------------------------------------------------------

'''
Command line interface to lunchbox library
'''


@click.group()
def main():
    pass  # pragma: no cover


@main.command()
@click.argument('url', type=str, nargs=1)
@click.argument('channel', type=str, nargs=1)
@click.argument('message', type=str, nargs=1)
def slack(url, channel, message):
    '''
        Posts a slack message to a given channel.

          URL     - https://hooks.slack.com/services URL

          CHANNEL - slack channel name

          MESSAGE - message to be posted
    '''
    lbt.post_to_slack(url, channel, message)  # pragma: no cover


@main.command()
def bash_completion():
    '''
        BASH completion code to be written to a _lunchbox completion file.
    '''
    cmd = '_LUNCHBOX_COMPLETE=bash_source lunchbox'  # pragma: no cover
    result = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)  # pragma: no cover
    result.wait()  # pragma: no cover
    click.echo(result.stdout.read())  # pragma: no cover


@main.command()
def zsh_completion():
    '''
        ZSH completion code to be written to a _lunchbox completion file.
    '''
    cmd = '_LUNCHBOX_COMPLETE=zsh_source lunchbox'  # pragma: no cover
    result = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)  # pragma: no cover
    result.wait()  # pragma: no cover
    click.echo(result.stdout.read())  # pragma: no cover


if __name__ == '__main__':
    main()  # pragma: no cover
