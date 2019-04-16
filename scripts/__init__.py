"""
Package with onenv scripts.
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import os

SCRIPTS_DIR = os.path.dirname(os.path.realpath(__file__))
ONE_ENV_ROOT_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, '..'))
