"""
Module used for manipulating branch config for pull_artifacts one-env script.
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2019 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import os
from typing import Dict, Any, Optional

from ..yaml_utils import load_yaml
from . import DEFAULT_BRANCH, CURRENT_BRANCH


def branch_config_template_path() -> str:
    script_dir = os.path.dirname(os.path.realpath(__file__))
    template_path = os.path.join(script_dir, 'branch_config_template.yaml')
    return template_path


def coalesce_branch_config(branch_config_path: str,
                           current_branch: Optional[str],
                           default_branch: Optional[str]) -> Dict[str, Any]:
    branch_config = load_yaml(branch_config_path)

    if default_branch:
        branch_config[DEFAULT_BRANCH] = default_branch

    if current_branch:
        branch_config[CURRENT_BRANCH] = current_branch
    else:
        branch_config[CURRENT_BRANCH] = branch_config[DEFAULT_BRANCH]

    return branch_config
