"""
This package contains modules with functionality for managing data in
~/.one-env directory.
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import os


def get_host_home() -> str:
    return os.path.expanduser('~')


def get_one_env_directory() -> str:
    return os.path.join(get_host_home(), '.one-env')
