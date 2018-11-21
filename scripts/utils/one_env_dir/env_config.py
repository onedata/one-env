"""
Module used for manipulating deployment env config for one-env tool.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import os
from typing import Optional, Dict, Any

from ..yaml_utils import load_yaml, dump_yaml


def get_default_env_config() -> Dict[str, Any]:
    script_dir = os.path.dirname(os.path.realpath(__file__))
    template_path = os.path.join(script_dir, 'env_config_template.yaml')
    return load_yaml(template_path)


def coalesce(*, curr_deployment_dir: str,
             env_config_path: Optional[str] = None,
             scenario: Optional[str] = None,
             sources: bool = False,
             packages: bool = False,
             onezone_image: Optional[str] = None,
             oneprovider_image: Optional[str] = None,
             oneclient_image: Optional[str] = None,
             rest_cli_image: Optional[str] = None,
             luma_image: Optional[str] = None,
             no_pull: bool = False) -> None:

    default_config = get_default_env_config()
    custom_config = load_yaml(env_config_path) if env_config_path else {}

    # Merge configs - user specified config overwrites the default
    merged_config = {**default_config, **custom_config}

    # Account command line args, that overwrite everything with highest
    # priority
    if scenario:
        merged_config['scenario'] = scenario

    if sources:
        merged_config['sources'] = True

    if packages:
        merged_config['sources'] = False

    if onezone_image:
        merged_config['onezoneImage'] = onezone_image

    if oneprovider_image:
        merged_config['oneproviderImage'] = oneprovider_image

    if oneclient_image:
        merged_config['oneclientImage'] = oneclient_image

    if rest_cli_image:
        merged_config['onedataCliImage'] = rest_cli_image

    if luma_image:
        merged_config['lumaImage'] = luma_image

    if no_pull:
        merged_config['forceImagePull'] = False

    deployment_env_config_path = os.path.join(curr_deployment_dir,
                                              'env_config.yaml')
    dump_yaml(merged_config, deployment_env_config_path)
