"""
Module used for manipulating user config for one-env tool.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import os
# FIXME use config reader from readers
import yaml
import deployments_dir


# FIXME use config reader from readers
def load_yaml(path):
    with open(path) as f:
        return yaml.load(f)


# FIXME use config reader from readers
def write_yaml(data, path):
    with open(path, "w+") as f:
        yaml.safe_dump(data, f, default_flow_style=False)


def config_template_path():
    script_dir = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(script_dir, 'env_config_template.yaml')


def config_path(deployment_dir):
    return os.path.join(deployment_dir, 'env_config.yaml')


def uses_binaries(pod, app):
    deployment_dir = deployments_dir.current_deployment_dir()
    env_cfg = load_yaml(config_path(deployment_dir))

    binaries = env_cfg['binaries']
    if binaries is True:
        return True
    elif binaries is False:
        return False

    matched_services = list(filter(lambda s: s in pod, binaries.keys()))
    if len(matched_services) != 1:
        return False

    nodes = env_cfg['binaries'][matched_services[0]]
    matched_nodes = list(filter(lambda n: n in pod, nodes.keys()))
    if len(matched_nodes) != 1:
        return False

    return app in nodes[matched_nodes[0]]


def coalesce(output_path, env_config_path=None, scenario=None, binaries=None,
             packages=None, onezone_image=None, oneprovider_image=None,
             no_pull=None):

    default_config = load_yaml(config_template_path())
    custom_config = {}
    if env_config_path:
        custom_config = load_yaml(env_config_path)

    # Merge configs - user specified config overwrites the default
    merged_config = {**default_config, **custom_config}

    # Account command line args, that overwrite everything with highest priority
    if scenario:
        merged_config['scenario'] = scenario

    if binaries:
        merged_config['binaries'] = True

    if packages:
        merged_config['binaries'] = False

    if onezone_image:
        merged_config['onezoneImage'] = onezone_image

    if oneprovider_image:
        merged_config['oneproviderImage'] = oneprovider_image

    if no_pull:
        merged_config['forceImagePull'] = False

    write_yaml(merged_config, config_path(output_path))

    pass
