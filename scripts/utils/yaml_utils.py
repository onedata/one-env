"""
This module contains utilities for operations on yaml files.
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"


from typing import Dict, Any, Optional

import yaml


def load_yaml(path: str) -> Dict[Any, Any]:
    with open(path) as f:
        return yaml.load(f, Loader=yaml.Loader)


def dump_yaml(data: Dict[Any, Any],
              file_path: Optional[str] = None) -> Optional[str]:
    if file_path:
        with open(file_path, 'w+') as f:
            yaml.safe_dump(data, f, default_flow_style=False)
        return None
    return yaml.safe_dump(data, default_flow_style=False)
