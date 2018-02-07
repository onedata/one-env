"""
Creates values files based on custom user env config.
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"


import config.writers as writers
import os
import config_generator


def get_nodes_list(env_cfg, service):
    nodes = set(env_cfg[service].get('clusterConfig', {}).get('managers', []) +
                env_cfg[service].get('clusterConfig', {}).get('workers', []) +
                env_cfg[service].get('clusterConfig', {}).get('databases', []))
    return {node_name: {} for node_name in nodes}


def providers_mapping(name):
    return {'oneprovider-krakow': 'oneprovider-p1',
            'oneprovider-paris': 'oneprovider-p2',
            'oneprovider-p1': 'oneprovider-krakow',
            'oneprovider-p2': 'oneprovider-paris'}.get(name, name)


def parse_env_config(env_cfg, bin_cfg, scenario_key, scenario_path):
    new_env_cfg = {scenario_key: {}}

    force_image_pull = env_cfg.get('forceImagePull')
    oneprovider_image = env_cfg.get('oneproviderImage')
    onezone_image = env_cfg.get('onezoneImage')

    spaces_cfg = env_cfg.get('createSpaces')
    if isinstance(spaces_cfg, list):
        new_env_cfg['spaces'] = parse_spaces_cfg(spaces_cfg)
    if isinstance(spaces_cfg, bool) and not spaces_cfg:
        new_env_cfg['spaces'] = []

    for service in bin_cfg[scenario_key].keys():
        parse_service_cfg(new_env_cfg, env_cfg, service, scenario_key,
                          onezone_image, oneprovider_image, force_image_pull,
                          bin_cfg)

    writer = writers.ConfigWriter(new_env_cfg, 'yaml')
    with open(os.path.join(scenario_path, 'CustomConfig.yaml'), "w") as f:
        f.write(writer.dump())

    writer = writers.ConfigWriter(bin_cfg, 'yaml')
    with open(os.path.join(scenario_path, 'BinVal.yaml'), "w") as f:
        f.write(writer.dump())


def parse_node_binaries(bin_cfg, custom_bin_cfg, scenario_key, service):
    for node_name, node_binaries in custom_bin_cfg[providers_mapping(service)].items():
        node = {'binaries': [{'name': binary} for binary in node_binaries]}
        bin_cfg[scenario_key][service]['nodes'][node_name] = node


def parse_spaces_cfg(spaces_cfg):
    for space in spaces_cfg:
        for support in space.get('supports'):
            support['provider'] = providers_mapping(support['provider'])
    return spaces_cfg


def parse_service_cfg(new_env_cfg, env_cfg, service, scenario_key,
                      onezone_image, oneprovider_image, force_image_pull,
                      bin_cfg):
    new_env_cfg[scenario_key][service] = \
        {'image': onezone_image if 'onezone' in service else oneprovider_image}

    new_env_cfg[scenario_key][service]['imagePullPolicy'] = \
        'Always' if force_image_pull else 'IfNotPresent'

    custom_bin_cfg = env_cfg.get('binaries')
    service_cfg = env_cfg.get(providers_mapping(service))
    if service_cfg:
        # Get all nodes specified in clusterConfig part
        new_env_cfg[scenario_key][service]['nodes'] = \
            get_nodes_list(env_cfg, providers_mapping(service))

        batch_cfg = service_cfg.get('batchConfig')
        if isinstance(batch_cfg, bool) and not batch_cfg:
            new_env_cfg[scenario_key][service]['onepanel_batch_mode_enabled'] = False

        new_env_cfg[scenario_key][service] = \
            {**new_env_cfg[scenario_key][service],
             **env_cfg[providers_mapping(service)]}

    # Parse custom binaries. If some node wasn't specified in clusterConfig part
    # it should be automatically added
    if isinstance(custom_bin_cfg, dict) and custom_bin_cfg.get(providers_mapping(service)):
        parse_node_binaries(bin_cfg, custom_bin_cfg, scenario_key, service)

    # # Handle case where user want more than one node and uses binaries true option
    # if isinstance(custom_bin_cfg, bool) and custom_bin_cfg:
