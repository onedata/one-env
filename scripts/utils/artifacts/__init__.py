"""
This package contains modules with functionality for managing artifacts.
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2019 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import os


SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
LOCAL_ARTIFACTS_DIR = os.path.abspath(os.path.join(SCRIPT_DIR,
                                                   '../../../artifacts_dir'))
ARTIFACT_REPO_HOST_ENV = 'ARTIFACT_REPO_HOST'
ARTIFACT_REPO_PORT_ENV = 'ARTIFACT_REPO_PORT'
REPO_ARTIFACTS_DIR = 'artifacts'
ARTIFACTS_EXT = '.tar.gz'
DEFAULT_BRANCH = 'default'
DEVELOP_BRANCH = 'develop'
CURRENT_BRANCH = 'current_branch'
