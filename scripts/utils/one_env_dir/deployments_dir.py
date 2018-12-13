"""
Convenience functions that manipulate 'deployments' directory located in
~/.one-env.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import os
import sys
import time
import shutil
import datetime
import contextlib

from . import user_config
from .. import terminal
from ..common import random_string


def get_deployments_directory() -> str:
    return os.path.join(user_config.get_one_env_directory(), 'deployments')


def prune_deployments_history() -> None:
    limit = user_config.get('maxPersistentHistory')
    all_deployments = os.listdir(get_deployments_directory())
    all_deployments.sort(reverse=True)
    for deployment in all_deployments[limit:]:
        terminal.warning('Removing old deployment data as '
                         'maxPersistentHistory was reached: {}'
                         .format(deployment))
        shutil.rmtree(os.path.join(get_deployments_directory(), deployment))


def get_current_deployment_dir() -> str:
    all_deployments = os.listdir(get_deployments_directory())
    all_deployments.sort()
    if not all_deployments:
        terminal.error('There are no deployments')
        sys.exit(1)
    else:
        return os.path.join(get_deployments_directory(), all_deployments[-1])


def get_current_log_dir() -> str:
    return os.path.join(get_current_deployment_dir(), 'logs')


def new() -> str:
    with contextlib.suppress(FileExistsError):
        os.mkdir(get_deployments_directory())

    dir_name = (datetime.datetime
                .fromtimestamp(time.time())
                .strftime('%Y.%m.%d-%H.%M.%S'))
    dir_path = os.path.join(get_deployments_directory(), dir_name)

    try:
        os.mkdir(dir_path)
    except FileExistsError:
        dir_path = '{}#{}'.format(dir_path, random_string(5))
        os.mkdir(dir_path)

    prune_deployments_history()

    return dir_path
