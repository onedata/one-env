"""
Creates values files based on custom user env config.
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"


import config.writers as writers
import os
import yaml
import config_generator


def parse_node_name(node_name):
    """Parse node name in form 'node-1' to 'n1'"""
    node_num = parse_node_num(node_name)
    return 'n{}'.format(node_num)


def parse_node_num(node_name):
    node_num = node_name.replace('node-', '')

    # Because k8s numerates from 0
    node_num = int(node_num) - 1

    return '{}'.format(node_num)


def get_nodes_list(service_cfg):
    nodes = set(service_cfg.get('clusterConfig', {}).get('managers', []) +
                service_cfg.get('clusterConfig', {}).get('workers', []) +
                service_cfg.get('clusterConfig', {}).get('databases', []))

    nodes_dict = {}

    for node_name in nodes:
        nodes_dict[parse_node_name(node_name)] = {}

    return nodes_dict


def providers_mapping(name):
    return {'oneprovider-krakow': 'oneprovider-1',
            'oneprovider-paris': 'oneprovider-2',
            'oneprovider-lisbon': 'oneprovider-3',
            'oneprovider-1': 'oneprovider-krakow',
            'oneprovider-2': 'oneprovider-paris',
            'oneprovider-3': 'oneprovider-lisbon'}.get(name, name)


def parse_env_config(env_cfg, base_sources_cfg, scenario_key, scenario_path):
    parsed_env_cfg = {
        scenario_key: {}
    }

    force_image_pull = env_cfg.get('forceImagePull')
    oneprovider_image = env_cfg.get('oneproviderImage')
    onezone_image = env_cfg.get('onezoneImage')
    oneclient_image = env_cfg.get('oneclientImage')

    spaces_cfg = env_cfg.get('createSpaces')
    parse_spaces_cfg(spaces_cfg, parsed_env_cfg)

    oneclients_cfg = env_cfg.get('oneclients')
    if oneclients_cfg:
        parsed_env_cfg['oneclient'] = {'enabled': True}

    onedata_cli_cfg = env_cfg.get('onedata-cli')
    if onedata_cli_cfg:
        parsed_env_cfg['onedata-cli'] = {'enabled': True}

    for service in base_sources_cfg[scenario_key].keys():
        parse_service_cfg(parsed_env_cfg, env_cfg, service, scenario_key,
                          onezone_image, oneprovider_image, oneclient_image,
                          force_image_pull, base_sources_cfg)

    writer = writers.ConfigWriter(parsed_env_cfg, 'yaml')
    with open(os.path.join(scenario_path, 'CustomConfig.yaml'), "w") as f:
        f.write(writer.dump())

    writer = writers.ConfigWriter(base_sources_cfg, 'yaml')
    with open(os.path.join(scenario_path, 'SourcesVal.yaml'), "w") as f:
        f.write(writer.dump())


def parse_service_cfg(parsed_env_cfg, env_cfg, service, scenario_key,
                      onezone_image, oneprovider_image, oneclient_image,
                      force_image_pull, base_sources_cfg):
    service_type = 'onezone' if 'onezone' in service else 'oneprovider'

    parsed_env_cfg[scenario_key][service] = \
        {'image': onezone_image if 'onezone' in service else oneprovider_image}

    parsed_env_cfg[scenario_key][service]['imagePullPolicy'] = \
        'Always' if force_image_pull else 'IfNotPresent'

    nodes = {}

    custom_sources_cfg = env_cfg.get('sources')
    service_cfg = env_cfg.get(providers_mapping(service))
    if service_cfg:
        # Get all nodes specified in clusterConfig part
        nodes = get_nodes_list(service_cfg)
        parsed_env_cfg[scenario_key][service]['nodes'] = nodes

        cluster_cfg = service_cfg.get('clusterConfig')
        parse_cluster_config(cluster_cfg, parsed_env_cfg[scenario_key][service])

        # Add sources for additional nodes
        if isinstance(custom_sources_cfg, bool) and custom_sources_cfg:
            add_sources_for_nodes(parsed_env_cfg[scenario_key][service]['nodes'],
                                  base_sources_cfg, scenario_key, service)

        batch_cfg = service_cfg.get('batchConfig')
        if isinstance(batch_cfg, bool) and not batch_cfg:
            parsed_env_cfg[scenario_key][service]['onepanel_batch_mode_enabled'] = False
        if isinstance(batch_cfg, dict):
            users_cfg = batch_cfg.get('createUsers')
            parse_users_config(users_cfg, parsed_env_cfg[scenario_key][service])

        parsed_env_cfg[scenario_key][service] = \
            {**parsed_env_cfg[scenario_key][service],
             **env_cfg[providers_mapping(service)]}

    # Parse custom sources. If some node wasn't specified in clusterConfig part
    # it should be automatically added
    if isinstance(custom_sources_cfg, dict):
        parse_node_sources(base_sources_cfg, custom_sources_cfg, scenario_key,
                           service)
        nodes = base_sources_cfg[scenario_key][service]['sources_cfg']['nodes']

    set_nodes_num(parsed_env_cfg, service_type, scenario_key, service, nodes)


def parse_node_sources(base_sources_cfg, custom_sources_cfg, scenario_key,
                       service):
    parsed_nodes_cfg = {}

    # clean default configuration
    for node_name in base_sources_cfg[scenario_key].get(service).get('sources_cfg').get('nodes').keys():
        parsed_nodes_cfg[node_name] = {}

    base_sources_cfg[scenario_key][service]['sources_cfg']['nodes'] = parsed_nodes_cfg

    if custom_sources_cfg.get(providers_mapping(service)):
        # parse custom configuration
        for node_name, node_sources in custom_sources_cfg[providers_mapping(service)].items():
            node_name = parse_node_name(node_name)
            node = {'sources': [{'name': source} for source in node_sources]}
            base_sources_cfg[scenario_key][service]['sources_cfg']['nodes'][node_name] = node


def add_sources_for_nodes(nodes_list, base_sources_cfg, scenario_key, service):
    for node_name in nodes_list:
        base_sources_cfg[scenario_key][service]['sources_cfg']['nodes'][node_name] = \
            base_sources_cfg[scenario_key][service]['sources_cfg']['nodes']['n0']


def parse_spaces_cfg(spaces_cfg, new_env_cfg):
    if isinstance(spaces_cfg, bool) and not spaces_cfg:
        new_env_cfg['spaces'] = []
    if isinstance(spaces_cfg, list):
        for space in spaces_cfg:
            for support in space.get('supports'):
                support['provider'] = providers_mapping(support['provider'])
        new_env_cfg['spaces'] = spaces_cfg


def set_nodes_num(config, service_type, scenario_key, service, nodes_list):
    nodes_count_key = '{}_nodes_count'.format(service_type)
    config[scenario_key][service][nodes_count_key] = max(len(nodes_list), 1)


def parse_users_config(users_cfg, parsed_users_cfg: dict):

    if isinstance(users_cfg, bool) and not users_cfg:
        parsed_users_cfg['onepanel_admin_users'] = []
        parsed_users_cfg['onepanel_users'] = []
    elif isinstance(users_cfg, dict):
        admin_users = users_cfg.get('adminUsers')
        regular_users = users_cfg.get('regularUsers')

        parsed_users_cfg['onepanel_admin_users'] = admin_users
        parsed_users_cfg['onepanel_users'] = regular_users


def parse_cluster_config(cluster_cfg: dict, parsed_cluster_cfg: dict):
    if cluster_cfg:
        parsed_cluster_cfg['cluster_config'] = {}
        for key, nodes_list in cluster_cfg.items():
            parsed_cluster_cfg['cluster_config'][key] = \
                [parse_node_num(node_name) for node_name in nodes_list]
