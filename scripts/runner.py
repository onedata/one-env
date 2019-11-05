"""
Wrapper responsible for starting appropriate onenv_* command in one-env docker
container. If container does not exist it will be automatically created.
Image used to start container can be configured in ~/.one-env/config.
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2019 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import os
import re
import grp
import sys
import argparse
import webbrowser
from typing import List
import subprocess as sp

from .utils.shell import call, check_output
from .utils.terminal import error
from .utils import user_config
from . import ONE_ENV_CONTAINER_NAME, OPENING_URL_INFO
from .utils import docker


def get_environment_vars() -> List[docker.EnvVar]:
    env_variables = []
    env_variables_names = ['HOME', 'SSH_AUTH_SOCK', 'ARTIFACT_REPO_HOST',
                           'ARTIFACT_REPO_PORT']

    for variable_name in env_variables_names:
        if os.environ.get(variable_name):
            env_variables.append(docker.EnvVar(variable_name,
                                               os.environ.get(variable_name)))
    return env_variables


def get_volumes() -> List[docker.Volume]:
    volumes = [docker.Volume(os.environ.get('HOME'), os.environ.get('HOME')),
               docker.Volume('/etc/hosts', '/etc/hosts'),
               docker.Volume('/var/run/docker.sock', '/var/run/docker.sock')]

    if os.environ.get('SSH_AUTH_SOCK'):
        volumes.append(docker.Volume(os.environ.get('SSH_AUTH_SOCK'),
                                     os.environ.get('SSH_AUTH_SOCK')))
    return volumes


def run_one_env_docker() -> str:
    # user_config is necessary as it holds information about which version
    # of one-env docker should be used
    user_config.ensure_exists()
    cmd = docker.run(
        user_config.get_one_env_image(),
        user=docker.User(os.geteuid(), os.getegid()),
        work_dir=os.getcwd(),
        name=ONE_ENV_CONTAINER_NAME,
        envs=get_environment_vars(),
        volumes=get_volumes(),
        interactive=True,
        tty=True,
        detach=True,
        network='host',
        groups=[str(grp.getgrnam('docker').gr_gid)]
    )

    try:
        container = check_output(cmd)
    except sp.CalledProcessError as ex:
        error(ex.stdout.decode('utf-8')).strip()
        sys.exit(1)
    else:
        exec_cmd_in_one_env_docker(container, ['init'])
        return container


def exec_cmd_in_one_env_docker(container: str, args: List[str]) -> None:
    exec_cmd = docker.execute(
        container,
        tty=True,
        interactive=True,
        work_dir=os.getcwd(),
        user=docker.User(os.geteuid(), os.getegid()),
        envs=get_environment_vars(),
        command=['bash', '-c', 'onenv ' + ' '.join(args)]
    )

    try:
        res = check_output(exec_cmd)
        print(res)
        if OPENING_URL_INFO in res:
            url = re.search('{}(.*)'.format(OPENING_URL_INFO), res).group(1)
            webbrowser.open(url)
    except sp.CalledProcessError as ex:
        error(ex.stdout.decode('utf-8').strip())
        sys.exit(1)


def get_one_env_container() -> str:
    name_filter = docker.Filter('name', ONE_ENV_CONTAINER_NAME)
    container = check_output(docker.ps(all_containers=True, quiet=True,
                                       filters=[name_filter]))
    if container:
        status = docker.get_container_status(container)
        if status.lower() == docker.RUNNING_STATUS:
            return container
        call(docker.rm(container, force=True))
    return run_one_env_docker()


def run_one_env_cmd_in_docker(args: List[str]) -> None:
    container = get_one_env_container()
    exec_cmd_in_one_env_docker(container, args)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog='runner',
        add_help=False,
        description='Wrapper responsible for starting appropriate onenv_* '
                    'command in one-env docker container.'
    )

    _args, pass_args = parser.parse_known_args()
    run_one_env_cmd_in_docker(pass_args)


if __name__ == '__main__':
    main()
