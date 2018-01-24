"""
Convenience functions that manipulate 'deployments' directory located in
~/.one-env.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import os
import time
import datetime
import random
import string
import shutil
import sys
import user_config
import console


def deployments_directory():
    return os.path.join(user_config.one_env_directory(), 'deployments')


def random_string():
    return ''.join([random.choice(string.ascii_letters) for _ in range(5)])


def prune_deployments_history():
    limit = user_config.get('maxPersistentHistory')
    all_deployments = os.listdir(deployments_directory())
    all_deployments.sort()
    while len(all_deployments) > limit:
        oldest = all_deployments.pop(0)
        console.warning('Removing old deployment data as maxPersistentHistory '
                        'was reached: {}'.format(oldest))
        shutil.rmtree(os.path.join(deployments_directory(), oldest))


def current_deployment_dir():
    all_deployments = os.listdir(deployments_directory())
    if len(all_deployments) == 0:
        console.error('There are no deployments')
        sys.exit(1)
    else:
        return os.path.join(deployments_directory(), all_deployments[-1])


def new():
    try:
        os.mkdir(deployments_directory())
    except FileExistsError:
        pass

    dir_name = datetime.datetime.fromtimestamp(time.time()).strftime(
        '%Y.%m.%d-%H.%M.%S')
    dir_name = os.path.join(deployments_directory(), dir_name)

    try:
        os.mkdir(dir_name)
    except FileExistsError:
        dir_name = '{}#{}'.format(dir_name, random_string())
        os.mkdir(dir_name)

    prune_deployments_history()

    return dir_name
