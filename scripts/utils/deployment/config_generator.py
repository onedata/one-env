"""
Overrides app.config files based on given sources configuration.
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import os
from typing import Dict, List, Tuple

from .node import Node
from .. import yaml_utils
from . import sources_paths
from ..common import get_curr_time
from .application import Application
from ..one_env_dir import user_config
from ..names_and_paths import (SERVICE_ONEZONE, ONEZONE_APPS, ONEPROVIDER_APPS,
                               SERVICE_ONECLIENT, get_matching_oneclient,
                               get_service_type)

ROOT_PATH = '/'


def generate_app_config(app_name: str, node_name: str,
                        node_config: Dict[str, List], service: str,
                        host_home_dir: str,
                        deploy_from_sources: bool) -> Tuple[Dict[str, str],
                                                            bool]:
    src_outside_home_dir = False
    app_config = {'name': app_name}
    service_type = get_service_type(service)

    if (deploy_from_sources and any(a['name'] == app_name for a in
                                    node_config.get('sources', []))):
        sources_path = os.path.abspath(sources_paths.locate_oz_op(app_name,
                                                                  service,
                                                                  service_type,
                                                                  node_name))

        if sources_path.startswith('/home'):
            app_config['hostPath'] = os.path.relpath(sources_path,
                                                     host_home_dir)
        else:
            src_outside_home_dir = True
            app_config['hostPath'] = sources_path

    else:
        app_config['hostPath'] = ''

    return app_config, src_outside_home_dir


def generate_nodes_config(scenario_sources_cfg: Dict[str, Dict], service: str,
                          host_home_dir: str, env_config_dir_path: str,
                          nodes_cfg: Dict[str, Dict]) -> Dict[str, Dict]:
    new_nodes_config = {}
    service_sources_cfg = scenario_sources_cfg[service]
    src_outside_home_dir = False

    if SERVICE_ONEZONE in service:
        service_apps = ONEZONE_APPS
    else:
        service_apps = ONEPROVIDER_APPS

    nodes_configs = service_sources_cfg['deployFromSources']['nodes']

    for node_name, node_config in nodes_configs.items():
        node_apps = []
        node_sources_conf = []
        deploy_from_sources = service_sources_cfg['deployFromSources']['enabled']

        for app_name in service_apps:
            app_config, src_outside_home_dir = generate_app_config(app_name,
                                                                   node_name,
                                                                   node_config,
                                                                   service,
                                                                   host_home_dir,
                                                                   deploy_from_sources)
            if src_outside_home_dir:
                node_apps.append(Application(app_name, app_config['hostPath'],
                                             ROOT_PATH))
            else:
                node_apps.append(Application(app_name, app_config['hostPath'],
                                             host_home_dir))

            node_sources_conf.append(app_config)

        node = Node(node_name, node_apps, service, env_config_dir_path)
        node.add_node_to_nodes_cfg(nodes_cfg)

        new_nodes_config[node_name] = {'sources': node_sources_conf}

    if src_outside_home_dir:
        # not using ROOT_PATH here cause in charts we use '/' in path
        # concatenation so it will be appended there
        service_sources_cfg['hostPathPrefix'] = ''
        service_sources_cfg['vmPathPrefix'] = ''
        service_sources_cfg['deploymentDir'] = os.path.relpath(
            env_config_dir_path, ROOT_PATH)

    return new_nodes_config


def generate_configs(sources_cfg: Dict[str, Dict], sources_cfg_path: str,
                     scenario_key: str, deployment_dir: str) -> Dict[str, Dict]:
    sources_cfg = sources_cfg[scenario_key]
    home_dir_path = user_config.get('hostHomeDir')
    kube_home_dir_path = user_config.get('kubeHostHomeDir')
    nodes_cfg = {}

    for service in sources_cfg:
        service_cfg = sources_cfg[service]
        service_cfg['hostPathPrefix'] = home_dir_path
        service_cfg['vmPathPrefix'] = kube_home_dir_path
        service_cfg['deploymentDir'] = os.path.relpath(
            deployment_dir, home_dir_path)

        service_dir_path = os.path.join(deployment_dir, service)
        os.mkdir(service_dir_path)

        # client is always attached to some provider
        oneclient_cfg = service_cfg.get(SERVICE_ONECLIENT)
        if oneclient_cfg:
            deploy_from_sources_cfg = oneclient_cfg.get('deployFromSources')
            sources_enabled = deploy_from_sources_cfg.get('enabled')
            if sources_enabled:
                sources_type = deploy_from_sources_cfg.get('type')
                sources_paths.locate_oc(SERVICE_ONECLIENT,
                                        get_matching_oneclient(service),
                                        sources_type=sources_type)

        nodes_cfg[service] = {}
        service_nodes_cfg = generate_nodes_config(sources_cfg, service,
                                                  home_dir_path,
                                                  deployment_dir,
                                                  nodes_cfg)
        service_cfg['deployFromSources']['nodes'] = service_nodes_cfg
        service_cfg['deployFromSources']['timestamp'] = get_curr_time()
    sources_cfg = {scenario_key: sources_cfg}

    yaml_utils.dump_yaml(sources_cfg, sources_cfg_path)

    return nodes_cfg
