"""
Configure values files based on custom user configuration.
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import os
import itertools
from typing import Dict, List, IO, Any

from ..yaml_utils import load_yaml, dump_yaml
from ..names_and_paths import (service_name_to_alias_mapping, get_service_type,
                               SERVICE_ONEPROVIDER, get_matching_oneclient,
                               SERVICE_ONECLIENT)


# TODO: remove after keys in one-env cfg and chart will be the same
IMAGE_KEY_MAPPING = {
    'onezoneImage': 'oz_image',
    'oneclientImage': 'oc_image',
    'oneproviderImage': 'op_image',
    'onedataCliImage': 'cli_image',
    'lumaImage': 'luma_image'
}


def set_release_name_override(cfg: Dict[str, Dict], release_name: str) -> None:
    global_cfg = cfg.get('global', {})
    global_cfg['releaseNameOverride'] = release_name
    cfg['global'] = global_cfg


def set_onezone_main_admin(cfg: Dict[str, Dict],
                           admin_creds: List[str]) -> None:
    global_cfg = cfg.get('global', {})
    if not global_cfg.get('onezoneMainAdmin'):
        admin_username, admin_password = admin_creds
        global_cfg['onezoneMainAdmin'] = {'name': admin_username,
                                          'password': admin_password}
    cfg['global'] = global_cfg


def set_emergency_credentials(cfg: Dict[str, Dict], creds: List[str]) -> None:
    global_cfg = cfg.get('global', {})
    if not global_cfg.get('onepanelEmergencyAccount'):
        username, password = creds
        global_cfg['onepanelEmergencyAccount'] = {'name': username,
                                                  'password': password}
    cfg['global'] = global_cfg


def enable_oneclients(my_values_file: IO[Any]) -> None:
    my_values_file.write('oneclients_enabled: &oneclients_enabled true\n')


def parse_my_values(my_values_path: str, env_cfg: Dict[str, Any]) -> None:
    with open(my_values_path, 'a') as f:
        f.write('\n')
        for env_cfg_key, chart_key in IMAGE_KEY_MAPPING.items():
            image = env_cfg.get(env_cfg_key)
            if image:
                f.write('{0}: &{0} {1}\n'.format(chart_key, image))

        if env_cfg.get('luma'):
            f.write('{0}: &{0} true\n'.format('luma_enabled'))

        if env_cfg.get('oneclients'):
            enable_oneclients(f)

        if env_cfg.get('onedataCli'):
            f.write('{0}: &{0} true\n'.format('onedata_cli_enabled'))

        if env_cfg.get('persistence'):
            f.write('{0}: &{0} true\n'.format('onedata_persistence'))

        if env_cfg.get('elasticSearch'):
            f.write('{0}: &{0} true\n'.format('elasticsearch_enabled'))

        storages = env_cfg.get('storages', [])
        for storage in storages:
            if isinstance(storage, str):
                f.write('{0}_enabled: &{0}_enabled true\n'.format(storage))
            else:
                storage_name = list(storage.keys())[0]
                f.write('{0}_enabled: &{0}_enabled true\n'.format(
                    storage_name))
                if storage.get(storage_name).get('luma'):
                    f.write('luma_enabled_{0}: &luma_enabled_{0} '
                            'true\n'.format(storage_name))


def parse_node_name(node_name: str) -> str:
    """Parse node name in form 'node-1' to 'n1'"""
    node_num = parse_node_num(node_name)
    return 'n{}'.format(node_num)


def parse_node_num(node_name: str) -> str:
    node_num = node_name.replace('node-', '')

    # Because k8s numerates from 0
    node_num = int(node_num) - 1

    return '{}'.format(node_num)


def get_nodes_dict(service_cfg: Dict[str, Dict]) -> Dict[str, Dict]:
    nodes = set(itertools.chain.from_iterable(service_cfg.get('clusterConfig',
                                                              {}).values()))
    nodes_dict = {parse_node_name(node_name): {} for node_name in nodes}
    return nodes_dict


def enable_sources(cfg: Dict[str, Any]) -> None:
    cfg['deployFromSources']['enabled'] = True


def parse_env_config(env_cfg: Dict[str, Any], base_sources_cfg_path: str,
                     scenario_key: str, scenario_path: str,
                     my_values_path: str) -> Dict[str, Dict]:
    parsed_env_cfg = {
        scenario_key: {}
    }
    parsed_sources_cfg = load_yaml(base_sources_cfg_path)

    parse_my_values(my_values_path, env_cfg)
    force_image_pull = env_cfg.get('forceImagePull')
    image_pull_policy = 'Always' if force_image_pull else 'IfNotPresent'

    parsed_env_cfg['global'] = {'imagePullPolicy': image_pull_policy}
    if env_cfg.get('luma'):
        parsed_env_cfg['lumaJobEnabled'] = True

    spaces_cfg = env_cfg.get('createSpaces')
    parse_spaces_cfg(spaces_cfg, parsed_env_cfg)

    for service in parsed_sources_cfg[scenario_key].keys():
        parse_service_cfg(parsed_env_cfg, env_cfg, service, scenario_key,
                          parsed_sources_cfg, my_values_path)

    dump_yaml(parsed_env_cfg, os.path.join(scenario_path,
                                           'CustomConfig.yaml'))
    dump_yaml(parsed_sources_cfg, os.path.join(scenario_path,
                                               'SourcesVal.yaml'))
    return parsed_sources_cfg


def parse_service_cfg(parsed_env_cfg: Dict[str, Any],
                      env_cfg: Dict[str, Any], service: str, scenario_key: str,
                      parsed_src_cfg: Dict[str, Dict],
                      my_values_path: str) -> None:
    service_type = get_service_type(service)
    parsed_env_cfg[scenario_key][service] = {}
    nodes = {}
    custom_src_cfg = env_cfg.get('sources')
    service_src_cfg = parsed_src_cfg[scenario_key][service]

    if isinstance(custom_src_cfg, bool) and custom_src_cfg:
        enable_sources(service_src_cfg)
        if service_type == SERVICE_ONEPROVIDER:
            if env_cfg.get('oneclients'):
                enable_sources(service_src_cfg['oneclient'])

    service_cfg = env_cfg.get(service_name_to_alias_mapping(service))
    if service_cfg:
        # Get all nodes specified in clusterConfig part
        nodes = get_nodes_dict(service_cfg)
        parsed_env_cfg[scenario_key][service]['nodes'] = nodes

        cluster_cfg = service_cfg.get('clusterConfig')
        parse_cluster_config(cluster_cfg, parsed_env_cfg[scenario_key][service])
        if cluster_cfg:
            service_cfg.pop('clusterConfig')

        # Add sources for additional nodes
        if isinstance(custom_src_cfg, bool) and custom_src_cfg:
            add_sources_for_nodes(parsed_env_cfg[scenario_key][service]['nodes'],
                                  parsed_src_cfg, scenario_key, service)

        batch_cfg = service_cfg.get('batchConfig')
        if isinstance(batch_cfg, bool) and not batch_cfg:
            turn_off_batch_config(service_type,
                                  parsed_env_cfg[scenario_key][service])

        if isinstance(batch_cfg, dict):
            users_cfg = batch_cfg.get('createUsers')
            parse_users_config(users_cfg,
                               parsed_env_cfg[scenario_key][service])

        parsed_env_cfg[scenario_key][service] = {
            **parsed_env_cfg[scenario_key][service],
            **env_cfg[service_name_to_alias_mapping(service)]
        }

    # Parse custom sources. If some node wasn't specified in clusterConfig part
    # it should be automatically added
    if isinstance(custom_src_cfg, dict):
        if service_name_to_alias_mapping(service) in custom_src_cfg:
            enable_sources(service_src_cfg)
            parse_custom_sources_for_oz_op(parsed_src_cfg, custom_src_cfg,
                                           scenario_key, service)
            nodes = parsed_src_cfg[scenario_key][service]['deployFromSources']['nodes']
        if service_type == SERVICE_ONEPROVIDER:
            parse_custom_sources_for_oc(service, custom_src_cfg,
                                        service_src_cfg, my_values_path)

    set_nodes_num(parsed_env_cfg, service_type, scenario_key, service, nodes)


def turn_off_batch_config(service_type: str, service_cfg: Dict[str, Any]):
    service_cfg['onepanel_batch_mode_enabled'] = False
    if service_type == SERVICE_ONEPROVIDER:
        service_cfg['oneprovider_ready_check'] = {'enabled': False}
        service_cfg['wait-for-onezone'] = {'enabled': False}
    else:
        service_cfg['onezone_ready_check'] = {'enabled': False}


def parse_custom_sources_for_oc(provider_name: str,
                                custom_src_cfg: Dict[str, Any],
                                service_src_cfg: Dict[str, Any],
                                my_values_path: str) -> None:
    oneclient_name = get_matching_oneclient(provider_name)
    oneclient_alias = service_name_to_alias_mapping(oneclient_name)
    if oneclient_alias in custom_src_cfg:
        with open(my_values_path, 'a') as f:
            enable_oneclients(f)
        oneclient_cfg = service_src_cfg[SERVICE_ONECLIENT]
        enable_sources(oneclient_cfg)
        if isinstance(custom_src_cfg[oneclient_alias], str):
            src_type = custom_src_cfg[oneclient_alias]
            oneclient_cfg['deployFromSources']['type'] = src_type


def parse_custom_sources_for_oz_op(base_sources_cfg: Dict[str, Dict],
                                   custom_sources_cfg: Dict[str, Dict],
                                   scenario_key: str,
                                   service: str) -> None:
    parsed_nodes_cfg = {node_name: {}
                        for node_name in base_sources_cfg[scenario_key]
                        .get(service)
                        .get('deployFromSources')
                        .get('nodes')
                        .keys()}

    deploy_from_sources = base_sources_cfg[scenario_key][service]['deployFromSources']
    deploy_from_sources['nodes'] = parsed_nodes_cfg

    # parse custom configuration
    service_sources_cfg = custom_sources_cfg.get(service_name_to_alias_mapping(service))
    if service_sources_cfg:
        for node_name, node_sources in service_sources_cfg.items():
            node_name = parse_node_name(node_name)
            node = {'sources': [{'name': source} for source in node_sources]}
            deploy_from_sources['nodes'][node_name] = node


def add_sources_for_nodes(nodes_list: List, base_sources_cfg: Dict[str, Dict],
                          scenario_key: str, service: str) -> None:
    nodes = base_sources_cfg[scenario_key][service]['deployFromSources']['nodes']
    base_node_sources = nodes['n0']

    for node_name in nodes_list:
        nodes[node_name] = base_node_sources


def set_nodes_num(config: Dict[str, Any], service_type: str, scenario_key: str,
                  service: str, nodes_list: List) -> None:
    nodes_count_key = '{}_nodes_count'.format(service_type)
    config[scenario_key][service][nodes_count_key] = max(len(nodes_list), 1)


def parse_cluster_config(cluster_cfg: dict, parsed_cluster_cfg: dict) -> None:
    if cluster_cfg:
        parsed_cluster_cfg['cluster_config'] = {}
        for key, nodes_list in cluster_cfg.items():
            parsed_cluster_cfg['cluster_config'][key] = \
                [parse_node_num(node_name) for node_name in nodes_list]


def get_provider_suffix(provider_name: str) -> str:
    provider_alias = service_name_to_alias_mapping(provider_name)
    return provider_alias.split('-')[-1]


def get_default_group_idp(patch: bool = False) -> Dict[str, Dict]:
    default_idp = {
        'onezone': {
            'enabled': True,
            'mode': 'duringCrossSupportJob'
                    if patch
                    else 'duringKeycloakDeployment'
        }
    }
    return default_idp


def get_default_user_idp(user_type: str = 'regular',
                         patch: bool = False) -> Dict[str, Dict]:
    default_idp = {
        'onepanel': {
            'mode': 'rest' if patch else 'config',
            'enabled': True,
            'type': user_type
        }
    }
    return default_idp


def parse_groups_config(groups_cfg: List[Dict],
                        parsed_cfg: Dict[str, Any],
                        patch: bool = False) -> None:
    """
    groups:
        - name: group1
        - name: group2
    """
    if isinstance(groups_cfg, bool) and not groups_cfg:
        parsed_cfg['groups'] = []
    else:
        for group in groups_cfg:
            if not group.get('idps'):
                group['idps'] = get_default_group_idp(patch)
            if group.get('luma'):
                group['luma'] = parse_luma_cfg(group.get('luma', []),
                                               parsed_cfg)
    parsed_cfg['groups'] = groups_cfg


def parse_users_config(users_cfg: List[Dict],
                       parsed_cfg: Dict[str, Any],
                       patch: bool = False) -> None:
    """
    users:
        - name: user1
          password: password
          type: regular
          groups:
            - *group1
    """
    if isinstance(users_cfg, bool) and not users_cfg:
        parsed_cfg['users'] = []
    else:
        for user in users_cfg:
            if not user.get('idps'):
                user['idps'] = get_default_user_idp(user.get('type', 'regular'),
                                                    patch)
            if user.get('luma'):
                user['luma'] = parse_luma_cfg(user.get('luma', []),
                                              parsed_cfg)
        parsed_cfg['users'] = users_cfg


def parse_spaces_cfg(spaces_cfg: List[Dict],
                     parsed_cfg: Dict[str, Any]) -> None:
    if isinstance(spaces_cfg, bool) and not spaces_cfg:
        parsed_cfg['spaces'] = []
    if isinstance(spaces_cfg, list):
        for space in spaces_cfg:
            if space.get('owner'):
                space['user'] = space.get('owner')
            for support in space.get('supports', []):
                support['provider'] = get_provider_suffix(support['provider'])
                if support.get('luma'):
                    enable_luma_job(parsed_cfg)
        parsed_cfg['spaces'] = spaces_cfg


def enable_luma_job(cfg: Dict[str, Any]) -> None:
    cfg['lumaJobEnabled'] = True


def parse_luma_cfg(luma_cfg: List[Dict], cfg: Dict[str, Any]) -> List[Dict]:
    parsed_luma_cfg = []
    enable_luma_job(cfg)

    for prov_cfg in luma_cfg:
        prov_cfg['name'] = get_provider_suffix(prov_cfg.get('provider'))
        del prov_cfg['provider']
        parsed_luma_cfg.append(prov_cfg)

    return parsed_luma_cfg
