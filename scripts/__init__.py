"""
This package contains modules with utility functions for one_env scripts.
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import os
ONE_ENV_CONTAINER_NAME = 'one-env'
OPENING_URL_INFO = 'Opening URL: '


def get_host_home() -> str:
    return os.path.expanduser('~')


def get_one_env_directory() -> str:
    return os.path.join(get_host_home(), '.one-env')
