"""
Convenience functions for manipulating deployments via helm.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import sys
import subprocess
from typing import List

from .. import terminal, shell
from ..one_env_dir import user_config
from ..names_and_paths import ONEDATA_CHART_REPO


def add_onedata_repo() -> None:
    terminal.info('Adding {} repo to helm repositories'
                  .format(ONEDATA_CHART_REPO))
    cmd = add_repo_cmd('onedata', ONEDATA_CHART_REPO)
    subprocess.call(cmd, stdout=None, stderr=subprocess.STDOUT)


def install_cmd(chart_path: str, values_paths: List[str],
                release_name: str = None) -> List[str]:
    if not release_name:
        release_name = user_config.get_current_release_name()
    helm_install_cmd = ['helm', 'install', chart_path, '--namespace',
                        user_config.get_current_namespace(),
                        '--name', release_name]

    for values_path in values_paths:
        helm_install_cmd.extend(['-f', values_path])
    return helm_install_cmd


def add_repo_cmd(name: str, url: str) -> List[str]:
    return ['helm', 'repo', 'add', name, url]


def get_deployment_cmd(name: str) -> List[str]:
    return ['helm', 'get', name]


def delete_release_cmd(name: str) -> List[str]:
    return ['helm', 'delete', '--purge', name]


def deployment_exists() -> bool:
    ret = shell.get_return_code(
        get_deployment_cmd(user_config.get_current_release_name())
    )
    return ret == 0


def clean_release(release_name: str = None) -> None:
    if not release_name:
        release_name = user_config.get_current_release_name()
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