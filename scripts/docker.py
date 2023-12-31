"""
This module contains functions facilitating operations on docker.
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2019 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import sys
import subprocess as sp
from collections import namedtuple
from typing import Optional, List, Union


RUNNING_STATUS = 'running'
EntryPointCmdType = Union[str, List[str]]

EnvVar = namedtuple('EnvVar', ['name', 'value'])

Volume = namedtuple('Volume', ['host_path', 'mount_path', 'options'])
# make options parameter optional
Volume.__new__.__defaults__ = ('', )

User = namedtuple('User', ['user', 'group'])
# make group parameter optional
User.__new__.__defaults__ = ('', )

Filter = namedtuple('Filter', ['key', 'value'])


def assemble_env_vars(envs: Optional[List[EnvVar]] = None) -> List[str]:
    tokens = []

    if envs:
        for env in envs:
            tokens.extend(['-e', '{}={}'.format(env.name, env.value)])

    return tokens


def assemble_volumes(volumes: Optional[Volume] = None) -> List[str]:
    tokens = []

    if volumes:
        for volume in volumes:
            volume_spec = '{}:{}'.format(volume.host_path, volume.mount_path)
            if volume.options:
                volume_spec += ':{}'.format(volume.options)
            tokens.extend(['-v', volume_spec])
    return tokens


def assemble_filters(filters: Optional[Filter] = None) -> List[str]:
    tokens = []

    if filters:
        for flt in filters:
            tokens.extend(['-f', '{}={}'.format(flt.key, flt.value)])
    return tokens


def assemble_groups(groups: Optional[List[str]]) -> List[str]:
    tokens = []

    if groups:
        for group in groups:
            tokens.extend(['--group-add', group])

    return tokens


# pylint: disable=invalid-name
def ps(*, all_containers: bool = False, quiet: bool = False,
       output: bool = False,
       filters: Optional[List[Filter]] = None) -> Union[str, int]:
    cmd = ['docker', 'ps']

    if all_containers:
        cmd.append('--all')
    if quiet:
        cmd.append('-q')

    cmd.extend(assemble_filters(filters))

    if output:
        return check_output_with_decode(cmd)

    return sp.call(cmd)


def rm(container: str, force: bool = False) -> int:
    cmd = ['docker', 'rm']

    if force:
        cmd.append('-f')

    cmd.append(container)

    return sp.call(cmd)
# pylint: enable=invalid-name


def run(image: str, *, name: Optional[str] = None,
        work_dir: Optional[str] = None, user: Optional[User] = None,
        network: Optional[str] = None, tty: bool = False, detach: bool = False,
        interactive: bool = False, remove: bool = False, output: bool = False,
        envs: Optional[List[EnvVar]] = None,
        volumes: Optional[List[Volume]] = None,
        groups: Optional[List[str]] = None,
        command: Optional[EntryPointCmdType] = None) -> Union[str, int]:
    cmd = ['docker', 'run']

    if name:
        cmd.extend(['--name', name])
    if work_dir:
        cmd.extend(['-w', work_dir])
    if user:
        cmd.extend(['-u', '{}:{}'.format(user.user, user.group)])
    if network:
        cmd.extend(['--network', network])
    if detach or sys.__stdin__.isatty():
        if tty:
            cmd.append('--tty')
        if interactive:
            cmd.append('-i')
    if detach:
        cmd.append('-d')
    if remove:
        cmd.append('--rm')

    cmd.extend(assemble_env_vars(envs))
    cmd.extend(assemble_volumes(volumes))
    cmd.extend(assemble_groups(groups))

    cmd.append(image)

    if command:
        cmd.extend(format_command(command))

    if output:
        return check_output_with_decode(cmd)

    return sp.call(cmd)


def execute(container: str, *, work_dir: Optional[str] = None,
            interactive: bool = False, tty: bool = False, output: bool = False,
            detach: bool = False, user: Optional[User] = None,
            envs: Optional[List[EnvVar]] = None,
            command: Optional[EntryPointCmdType] = None) -> Union[str, int]:
    cmd = ['docker', 'exec']

    if detach or sys.__stdin__.isatty():
        if interactive:
            cmd.append('-i')
        if tty:
            cmd.append('-t')
    if work_dir:
        cmd.extend(['-w', work_dir])
    if user:
        cmd.extend(['-u', '{}:{}'.format(user.user, user.group)])

    cmd.extend(assemble_env_vars(envs))

    cmd.append(container)

    if command:
        cmd.extend(format_command(command))

    if output:
        return check_output_with_decode(cmd)

    return sp.call(cmd)


def inspect(container: str, fmt: Optional[str] = None) -> str:
    cmd = ['docker', 'inspect']

    if fmt:
        cmd.extend(['--format', fmt])

    cmd.append(container)

    return check_output_with_decode(cmd)


def format_command(entry_point: Union[str, List]) -> List[str]:
    if isinstance(entry_point, List):
        return entry_point
    if isinstance(entry_point, str):
        return [entry_point]
    raise TypeError('Expected string or list for entry_point.\n '
                    'Got {}'.format(entry_point))


def get_container_status(container: str) -> str:
    return inspect(container, '{{ .State.Status }}')


def check_output_with_decode(cmd: List[str]) -> str:
    return sp.check_output(cmd).decode('utf-8').strip('\n')
