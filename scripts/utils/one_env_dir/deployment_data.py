"""
Module used for persisting deployment data.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import os
import re
import sys
from typing import Any, Dict

from .. import terminal
from ..one_env_dir import deployments_dir
from ..yaml_utils import load_yaml, dump_yaml
from ..names_and_paths import SERVICE_ONECLIENT


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


def delete_pod_from_sources(pod_name: str) -> None:
    curr_data = get(default={})
    try:
        curr_sources = curr_data.get('sources')
    except KeyError:
        return
    else:
        del curr_sources[pod_name]
    dump_yaml(curr_data, get_current_deployment_data_path())


def add_release(release: str) -> None:
    curr_data = get(default={})
    curr_releases = curr_data.setdefault('releases', [])
    curr_releases.append(release)
    dump_yaml(curr_data, get_current_deployment_data_path())


def add_to_src_cfg(cfg_key: str, pod_substring: str, app: str,
                   location: str) -> None:
    curr_data = get(default={})
    curr_cfg = curr_data.setdefault(cfg_key, {})
    pod_cfg = curr_cfg.setdefault(pod_substring, {})
    pod_cfg[app] = location
    put(curr_data)


def add_oneclient_deployment(oc_pod_substring: str, location: str) -> None:
    add_to_src_cfg('oc-deployments', oc_pod_substring, SERVICE_ONECLIENT,
                   location)


def add_source(pod_name: str, app: str, location: str) -> None:
    add_to_src_cfg('sources', pod_name, app, location)


def get_oc_deployment_name(deployment_substring: str,
                           oc_deployments: Dict[str, Any]) -> str:
    pattern = '.*{}.*'.format(deployment_substring.replace('-', '.*'))
    matching_deployments = [deployment_name
                            for deployment_name in oc_deployments.keys()
                            if re.match(pattern, deployment_name)]

    if not matching_deployments:
        terminal.error('Could not find given oc-deployments.\n'
                       'Current oc-deployments are:\n')
        print('\n'.join(name for name in oc_deployments.keys()))
        sys.exit(1)
    if len(matching_deployments) > 1:
        terminal.error('Matched too many oc-deployments.\n')
        print('\n'.join(name for name in matching_deployments))
        sys.exit(1)

    return matching_deployments[0]
