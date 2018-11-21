"""
Module used for persisting deployment data.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import os
from typing import Any, Dict

from ..one_env_dir import deployments_dir
from ..yaml_utils import load_yaml, dump_yaml


def get_current_deployment_data_path() -> str:
    return os.path.join(deployments_dir.get_current_deployment_dir(),
                        'deployment_data.yml')


def get(*, default: Any = None) -> Any:
    deployment_data_path = get_current_deployment_data_path()
    if os.path.isfile(deployment_data_path):
        return load_yaml(deployment_data_path)
    return default


def put(new_data: Dict[Any, Any]) -> None:
    curr_data = get(default={})
    overwritten = {**curr_data, **new_data}
    dump_yaml(overwritten, get_current_deployment_data_path())
