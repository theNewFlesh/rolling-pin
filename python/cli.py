#!/usr/bin/env python

from pathlib import Path
import argparse
import os
import re

# set's REPO to whatever the repository is named
REPO = Path(__file__).parents[1].absolute().name
REPO_PATH = Path(__file__).parents[1].absolute().as_posix()
# ------------------------------------------------------------------------------

'''
A CLI for developing and deploying a service deeply integrated with this
repository's structure. Written to be python version agnostic.
'''


def get_info():
    '''
    Returns:
        str: System args and environment as a dict.
    '''
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description='A CLI for developing and deploying {repo} containers.'.format(repo=REPO),
        usage='\n\tpython cli.py COMMAND [-a --args]=ARGS [-h --help]'
    )

    parser.add_argument('command',
                        metavar='command',
                        type=str,
                        nargs=1,
                        action='store',
                        help='''Command to run in {repo} service.

    bash      - Run BASH session inside {repo} container
    container - Display the Docker container id for {repo} service
    coverage  - Generate coverage report for {repo} service
    destroy   - Shutdown {repo} service and destroy its Docker image
    docs      - Generate documentation for {repo} service
    full-docs - Generates documentation, coverage report and inserts report link
    image     - Display the Docker image id for {repo} service
    lab       - Start a Jupyter lab server
    lint      - Run linting on {repo} service code
    publish   - Publish repository to python package index.
    python    - Run python interpreter session inside {repo} container
    remove    - Remove {repo} service Docker image
    restart   - Restart {repo} service
    start     - Start {repo} service
    stop      - Stop {repo} service
    test      - Run testing on {repo} service
'''.format(repo=REPO))

    parser.add_argument(
        '-a',
        '--args',
        metavar='args',
        type=str,
        nargs='+',
        action='store',
        help='Additional arguments to be passed. Be sure to include hyphen prefixes.'
    )

    temp = parser.parse_args()
    mode = temp.command[0]
    args = []
    if temp.args is not None:
        args = re.split(' +', temp.args[0])

    compose_path = Path(REPO_PATH, 'docker/docker-compose.yml')
    compose_path = compose_path.as_posix()

    user = '{}:{}'.format(os.geteuid(), os.getegid())

    info = dict(
        args=args,
        mode=mode,
        compose_path=compose_path,
        user=user
    )
    return info


# COMMANDS----------------------------------------------------------------------
def get_bash_command(info):
    '''
    Opens a bash session inside a running container.

    Args:
        info (dict): Info dictionary.

    Returns:
        str: Command.
    '''
    cmd = "{exec} bash".format(exec=get_docker_exec_command(info))
    return cmd


def get_container_id_command():
    '''
    Gets current container id.

    Returns:
        str: Command.
    '''
    cmd = 'docker ps | grep {repo} '.format(repo=REPO)
    cmd += "| head -n 1 | awk '{print $1}'"
    return cmd


def get_coverage_command(info):
    '''
    Runs pytest coverage.

    Args:
        info (dict): Info dictionary.

    Returns:
        str: Command.
    '''
    cmd = '{exec} mkdir -p /root/{repo}/docs; {test} '
    args = [
        '--cov=/root/{repo}/python',
        '--cov-config=/root/{repo}/docker/pytest.ini',
        '--cov-report=html:/root/{repo}/docs/htmlcov',
    ]
    args = ' '.join(args)
    cmd += ' ' + args

    cmd = cmd.format(
        repo=REPO,
        exec=get_docker_exec_command(info),
        test=get_test_command(info),
    )
    return cmd


def get_docs_command(info):
    '''
    Build documentation.

    Args:
        info (dict): Info dictionary.

    Returns:
        str: Fully resolved build docs command.
    '''
    cmd = '{exec} mkdir -p /root/{repo}/docs; '
    cmd += '{exec} sphinx-build /root/{repo}/sphinx /root/{repo}/docs; '
    cmd += '{exec} touch /root/{repo}/docs/.nojekyll; '
    cmd = cmd.format(
        repo=REPO,
        exec=get_docker_exec_command(info),
    )
    return cmd


def get_post_process_docs_command(info):
    '''
    Munge docs/index.html to include link to coverage report.

    Args:
        info (dict): Info dictionary.

    Returns:
        str: Fully resolved post process docs command.
    '''
    cmd = '{exec} python3.7 /root/{repo}/sphinx/post_process_docs.py'
    cmd = cmd.format(
        repo=REPO,
        exec=get_docker_exec_command(info),
    )
    return cmd


def get_image_id_command():
    '''
    Gets currently built image id.

    Returns:
        str: Command.
    '''
    cmd = 'docker image ls | grep {repo} '.format(repo=REPO)
    cmd += "| head -n 1 | awk '{print $3}'"
    return cmd


def get_lab_command(info):
    '''
    Start a jupyter lab server.

    Args:
        info (dict): Info dictionary.

    Returns:
        str: Command.
    '''
    cmd = '{exec} jupyter lab --allow-root --ip=0.0.0.0 --no-browser'
    cmd = cmd.format(exec=get_docker_exec_command(info))
    return cmd


def get_lint_command(info):
    '''
    Runs flake8 linting on python code.

    Args:
        info (dict): Info dictionary.

    Returns:
        str: Command.
    '''
    cmd = '{exec} flake8 /root/{repo}/python --config /root/{repo}/docker/flake8.ini'
    cmd = cmd.format(repo=REPO, exec=get_docker_exec_command(info))
    return cmd


def get_publish_command(info):
    '''
    Publish repository to python package index.

    Args:
        info (dict): Info dictionary.

    Returns:
        str: Command.
    '''
    cmd = '{exec} bash -c "'
    cmd += 'rm -rf /tmp/{repo}; '
    cmd += 'cp -r /root/{repo}/python /tmp/{repo}; '
    cmd += 'cp /root/{repo}/README.md /tmp/{repo}/README; '
    cmd += 'cp /root/{repo}/LICENSE /tmp/{repo}/LICENSE; '
    cmd += 'cp /root/{repo}/pip/setup.cfg /tmp/{repo}/; '
    cmd += 'cp /root/{repo}/pip/setup.py /tmp/{repo}/; '
    cmd += r"find /tmp/{repo} | grep -E '_test\.py$' | parallel rm -rf; "
    cmd += '"; '
    cmd += '{exec2} python setup.py sdist; '
    cmd += '{exec2} twine upload dist/*; '
    cmd += '{exec} rm -rf /tmp/{repo}; '
    cmd = cmd.format(
        repo=REPO,
        exec=get_docker_exec_command(info),
        exec2=get_docker_exec_command(info, '/tmp/' + REPO),
    )
    return cmd


def get_python_command(info):
    '''
    Opens a python interpreter inside a running container.

    Args:
        info (dict): Info dictionary.

    Returns:
        str: Command.
    '''
    cmd = "{exec} python3.7".format(exec=get_docker_exec_command(info))
    return cmd


def get_remove_image_command(info):
    '''
    Removes docker image.

    Args:
        info (dict): Info dictionary.

    Returns:
        str: Command.
    '''
    cmd = 'IMAGE_ID=$({image_command}); '
    cmd += 'docker image rm --force $IMAGE_ID'
    cmd = cmd.format(image_command=get_image_id_command())
    return cmd


def get_start_command(info):
    '''
    Starts up container.

    Args:
        info (dict): Info dictionary.

    Returns:
        str: Fully resolved docker-compose up command.
    '''
    cmd = '{compose} up --detach; cd $CWD'
    cmd = cmd.format(compose=get_docker_compose_command(info))
    return cmd


def get_stop_command(info):
    '''
    Shuts down container.

    Args:
        info (dict): Info dictionary.

    Returns:
        str: Fully resolved docker-compose down command.
    '''
    cmd = '{compose} down; cd $CWD'
    cmd = cmd.format(compose=get_docker_compose_command(info))
    return cmd


def get_test_command(info):
    '''
    Runs pytest.

    Args:
        info (dict): Info dictionary.

    Returns:
        str: Command.
    '''
    cmd = '{exec} '
    cmd += 'pytest /root/{repo}/python -c /root/{repo}/docker/pytest.ini {args}'
    cmd = cmd.format(
        repo=REPO,
        exec=get_docker_exec_command(info),
        args=' '.join(info['args']),
    )
    return cmd


# DOCKER------------------------------------------------------------------------
def get_docker_command(info):
    '''
    Get misc docker command.

    Args:age
        info (dict): Info dictionary.

    Returns:
        str: Command.
    '''
    cmd = 'CWD=$(pwd); '
    cmd += 'cd {repo_path}/docker; '
    cmd += 'REPO_PATH="{repo_path}" CURRENT_USER="{user}" IMAGE="{repo}" '
    cmd += 'docker {mode} {args}; cd $CWD'
    args = ' '.join(info['args'])
    cmd = cmd.format(
        repo=REPO,
        repo_path=REPO_PATH,
        user=info['user'],
        mode=info['mode'],
        args=args
    )
    return cmd


def get_docker_exec_command(info, working_directory=None):
    '''
    Gets docker exec command.

    Args:
        info (dict): Info dictionary.
        working_directory (str, optional): Working directory.

    Returns:
        str: Command.
    '''
    cmd = '{up_command}; '
    cmd += 'CONTAINER_ID=$({container_command}); '
    cmd += 'docker exec --interactive --tty --user \"root:root\" -e {env} '
    if working_directory is not None:
        cmd += '-w {} '.format(working_directory)
    cmd += '$CONTAINER_ID '
    cmd = cmd.format(
        env='PYTHONPATH="${PYTHONPATH}:' + '/root/{}/python" '.format(REPO),
        up_command=get_start_command(info),
        container_command=get_container_id_command(),
    )
    return cmd


def get_docker_compose_command(info):
    '''
    Gets docker-compose command.

    Args:
        info (dict): Info dictionary.

    Returns:
        str: Command.
    '''
    cmd = 'CWD=`pwd`; cd {repo_path}/docker; '
    cmd += 'REPO_PATH="{repo_path}" CURRENT_USER="{user}" IMAGE="{repo}" '
    cmd += 'docker-compose -p {repo} -f {compose_path} '
    cmd = cmd.format(
        repo=REPO,
        repo_path=REPO_PATH,
        user=info['user'],
        compose_path=info['compose_path'],
    )
    return cmd


# MAIN--------------------------------------------------------------------------
def main():
    '''
    Print different commands to stdout depending on mode provided to command.
    '''
    info = get_info()
    mode = info['mode']
    cmd = get_docker_command(info)

    if mode == 'bash':
        cmd = get_bash_command(info)

    elif mode == 'container':
        cmd = get_container_id_command()

    elif mode == 'coverage':
        cmd = get_coverage_command(info)

    elif mode == 'destroy':
        cmd = get_stop_command(info)
        cmd += '; ' + get_remove_image_command(info)

    elif mode == 'docs':
        cmd = get_docs_command(info)

    elif mode == 'full-docs':
        cmd = get_docs_command(info)
        cmd += '; ' + get_coverage_command(info)
        cmd += '; ' + get_post_process_docs_command(info)

    elif mode == 'image':
        cmd = get_image_id_command()

    elif mode == 'lab':
        cmd = get_lab_command(info)

    elif mode == 'lint':
        cmd = get_lint_command(info)

    elif mode == 'publish':
        cmd = get_publish_command(info)

    elif mode == 'python':
        cmd = get_python_command(info)

    elif mode == 'remove':
        cmd = get_remove_image_command(info)

    elif mode == 'restart':
        cmd = get_stop_command(info)
        cmd += '; ' + get_start_command(info)

    elif mode == 'start':
        cmd = get_start_command(info)

    elif mode == 'stop':
        cmd = get_stop_command(info)

    elif mode == 'test':
        cmd = get_test_command(info)

    # print is used instead of execute because REPO_PATH and CURRENT_USER do not
    # resolve in a subprocess and subprocesses do not give real time stdout.
    # So, running `command up` will give you nothing until the process ends.
    # `eval "[generated command] $@"` resolves all these issues.
    print(cmd)


if __name__ == '__main__':
    main()
