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
    return {'oneprovider-krakow': 'oneprovider-1',
            'oneprovider-paris': 'oneprovider-2',
            'oneprovider-lisbon': 'oneprovider-3',
            'oneprovider-1': 'oneprovider-krakow',
            'oneprovider-2': 'oneprovider-paris',
            'oneprovider-3': 'oneprovider-lisbon'}.get(name, name)


def parse_env_config(env_cfg, sources_cfg, scenario_key, scenario_path):
    new_env_cfg = {scenario_key: {}}

    force_image_pull = env_cfg.get('forceImagePull')
    oneprovider_image = env_cfg.get('oneproviderImage')
    onezone_image = env_cfg.get('onezoneImage')

    spaces_cfg = env_cfg.get('createSpaces')
    if isinstance(spaces_cfg, list):
        new_env_cfg['spaces'] = parse_spaces_cfg(spaces_cfg)
    if isinstance(spaces_cfg, bool) and not spaces_cfg:
        new_env_cfg['spaces'] = []

    for service in sources_cfg[scenario_key].keys():
        parse_service_cfg(new_env_cfg, env_cfg, service, scenario_key,
                          onezone_image, oneprovider_image, force_image_pull,
                          sources_cfg)

    writer = writers.ConfigWriter(new_env_cfg, 'yaml')
    with open(os.path.join(scenario_path, 'CustomConfig.yaml'), "w") as f:
        f.write(writer.dump())

    writer = writers.ConfigWriter(sources_cfg, 'yaml')
    with open(os.path.join(scenario_path, 'SourcesVal.yaml'), "w") as f:
        f.write(writer.dump())


def parse_node_sources(sources_cfg, custom_sources_cfg, scenario_key, service):
    # clean default configuration
    for node_name in sources_cfg[scenario_key].get(service).get('nodes').keys():
        sources_cfg[scenario_key][service]['nodes'][node_name] = {}

    if custom_sources_cfg.get(providers_mapping(service)):
        # parse custom configuration
        for node_name, node_sources in custom_sources_cfg[providers_mapping(service)].items():
            node = {'sources': [{'name': source} for source in node_sources]}
            sources_cfg[scenario_key][service]['nodes'][node_name] = node


def add_sources_for_nodes(nodes_list, sources_cfg, scenario_key, service):
    for node_name in nodes_list:
        sources_cfg[scenario_key][service]['nodes'][node_name] = \
            sources_cfg[scenario_key][service]['nodes']['node-1']


def parse_spaces_cfg(spaces_cfg):
    for space in spaces_cfg:
        for support in space.get('supports'):
            support['provider'] = providers_mapping(support['provider'])
    return spaces_cfg


def parse_service_cfg(new_env_cfg, env_cfg, service, scenario_key,
                      onezone_image, oneprovider_image, force_image_pull,
                      sources_cfg):
    new_env_cfg[scenario_key][service] = \
        {'image': onezone_image if 'onezone' in service else oneprovider_image}

    new_env_cfg[scenario_key][service]['imagePullPolicy'] = \
        'Always' if force_image_pull else 'IfNotPresent'

    custom_sources_cfg = env_cfg.get('sources')
    service_cfg = env_cfg.get(providers_mapping(service))
    if service_cfg:
        # Get all nodes specified in clusterConfig part
        new_env_cfg[scenario_key][service]['nodes'] = \
            get_nodes_list(env_cfg, providers_mapping(service))

        # Handle additional nodes
        if isinstance(custom_sources_cfg, bool) and custom_sources_cfg:
            add_sources_for_nodes(new_env_cfg[scenario_key][service]['nodes'],
                                  sources_cfg, scenario_key, service)

        batch_cfg = service_cfg.get('batchConfig')
        if isinstance(batch_cfg, bool) and not batch_cfg:
            new_env_cfg[scenario_key][service]['onepanel_batch_mode_enabled'] = False

        new_env_cfg[scenario_key][service] = \
            {**new_env_cfg[scenario_key][service],
             **env_cfg[providers_mapping(service)]}

    # Parse custom sources. If some node wasn't specified in clusterConfig part
    # it should be automatically added
    if isinstance(custom_sources_cfg, dict):
        parse_node_sources(sources_cfg, custom_sources_cfg, scenario_key, service)
