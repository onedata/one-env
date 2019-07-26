"""
Convenience functions for manipulating deployments via helm.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import sys
import subprocess
from typing import List, Optional, Tuple

from .. import terminal, shell
from ..one_env_dir import user_config
from ..one_env_dir.user_config import (get_current_release_name,
                                       get_current_namespace)
from ..deployment import CHARTS_VERSION
from ..names_and_paths import ONEDATA_CHART_REPO, CROSS_SUPPORT_JOB_REPO_PATH


SetValues = List[Tuple[str, str]]


def get_release_name(release_name: Optional[str]) -> str:
    if release_name is None:
        return user_config.get_current_release_name()
    return release_name


def add_onedata_repo() -> None:
    terminal.info('Adding {} repo to helm repositories'
                  .format(ONEDATA_CHART_REPO))
    cmd = add_repo_cmd('onedata', ONEDATA_CHART_REPO)
    subprocess.call(cmd, stdout=None, stderr=subprocess.STDOUT)


def install_cmd(chart_path: str, values_paths: List[str],
                release_name: Optional[str] = None) -> List[str]:
    if not release_name:
        release_name = get_current_release_name()
    helm_install_cmd = ['helm', 'install', chart_path, '--namespace',
                        get_current_namespace(), '--name', release_name]

    for values_path in values_paths:
        helm_install_cmd.extend(['-f', values_path])
    return helm_install_cmd


def add_repo_cmd(name: str, url: str) -> List[str]:
    return ['helm', 'repo', 'add', name, url]


def get_deployment_cmd(release_name: str) -> List[str]:
    return ['helm', 'get', release_name]


def delete_release_cmd(release_name: Optional[str] = None) -> List[str]:
    if not release_name:
        release_name = get_current_release_name()
    return ['helm', 'delete', '--purge', release_name]


def get_values_cmd(release_name: Optional[str] = None) -> List[str]:
    if not release_name:
        release_name = get_current_release_name()
    return ['helm', 'get', 'values', release_name]


def upgrade_cmd(set_values: Optional[SetValues] = None,
                values_files: Optional[List[str]] = None,
                release_name: Optional[str] = None,
                charts_path: Optional[str] = None) -> List[str]:
    if not release_name:
        release_name = get_current_release_name()

    cmd = ['helm', 'upgrade']

    if set_values:
        for (key, value) in set_values:
            cmd.extend(['--set', '{}={}'.format(key, value)])

    if values_files:
        for val_file in values_files:
            cmd.extend(['-f', val_file])

    if charts_path:
        cmd.extend([release_name, charts_path])
    else:
        cmd.extend([release_name, CROSS_SUPPORT_JOB_REPO_PATH])

    cmd.extend(['--version', CHARTS_VERSION])

    return cmd


def rollback_cmd(version: str = '0',
                 release_name: Optional[str] = None) -> List[str]:
    if not release_name:
        release_name = get_current_release_name()
    return ['helm', 'rollback', release_name, version]


def diff_cmd(cmd: List[str]) -> List[str]:
    return ['helm', 'diff'] + cmd


def deployment_exists(release_name: Optional[str] = None) -> bool:
    if not release_name:
        release_name = get_current_release_name()
    ret = shell.get_return_code(get_deployment_cmd(release_name))
    return ret == 0


def clean_release(release_name: Optional[str] = None) -> None:
    if not release_name:
        release_name = get_current_release_name()
    if deployment_exists(release_name):
        shell.call(delete_release_cmd(release_name))


def ensure_deployment(exists: bool = True,
                      fail_with_error: bool = False) -> None:
    if exists:
        log = 'There is no active deployment'
    else:
        log = 'There already is an active deployment'

    if exists is not deployment_exists():
        if fail_with_error:
            terminal.error(log)
            sys.exit(1)
        else:
            terminal.info(log)
            sys.exit(0)
