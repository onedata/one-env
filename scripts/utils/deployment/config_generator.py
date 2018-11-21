"""
Overrides app.config files based on given sources configuration.
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import os
from typing import Dict, List, Tuple

from .. import yaml_utils
from ..one_env_dir import user_config
from ..deployment import sources, node, application
from ..names_and_paths import SERVICE_ONEZONE, ONEZONE_APPS, ONEPROVIDER_APPS


ROOT_PATH = '/'


def generate_app_config(app_name: str, node_name: str,
                        node_config: Dict[str, List], service: str,
                        host_home_dir: str,
                        deploy_from_sources: bool) -> Tuple[Dict[str, str],
                                                            bool]:
    override_prefix = False
    app_config = {'name': app_name}

    if (deploy_from_sources and any(a['name'] == app_name for a in
                                    node_config.get('sources', []))):
        source_path = os.path.abspath(sources.locate(app_name,
                                                     service, node_name))

        if source_path.startswith('/home'):
            app_config['hostPath'] = os.path.relpath(source_path,
                                                     host_home_dir)
        else:
            override_prefix = True
            app_config['hostPath'] = source_path

    else:
        app_config['hostPath'] = ''

    return app_config, override_prefix


def generate_nodes_config(scenario_sources_cfg: Dict[str, Dict], service: str,
                          host_home_dir: str, env_config_dir_path: str,
                          nodes_cfg: Dict[str, Dict]) -> Dict[str, Dict]:
    new_nodes_config = {}
    override_prefix = False

    if SERVICE_ONEZONE in service:
        service_apps = ONEZONE_APPS
    else:
        service_apps = ONEPROVIDER_APPS

    nodes_configs = scenario_sources_cfg[service]['deployFromSources']['nodes']
    for node_name, node_config in nodes_configs.items():
        node_apps = []
        node_sources_conf = []
        deploy_from_sources = scenario_sources_cfg[service]['deployFromSources']['enabled']

        for app_name in service_apps:
            app_config, override_prefix = generate_app_config(app_name,
                                                              node_name,
                                                              node_config,
                                                              service,
                                                              host_home_dir,
                                                              deploy_from_sources)
            if override_prefix:
                node_apps.append(application.Application(app_name,
                                                         app_config['hostPath'],
                                                         ROOT_PATH))
            else:
                node_apps.append(application.Application(app_name,
                                                         app_config[
                                                             'hostPath'],
                                                         host_home_dir))

            node_sources_conf.append(app_config)

        nodes_cfg[service][node_name] = node.Node(node_name, node_apps,
                                                  service, env_config_dir_path)
        new_nodes_config[node_name] = {'sources': node_sources_conf}

    if override_prefix:
        # not using ROOT_PATH here cause in charts we use '/' in path
        # concatenation so it will be appended there
        scenario_sources_cfg[service]['hostPathPrefix'] = ''
        scenario_sources_cfg[service]['vmPathPrefix'] = ''
        scenario_sources_cfg[service]['deploymentDir'] = os.path.relpath(
            env_config_dir_path, ROOT_PATH)

    return new_nodes_config


def generate_configs(sources_cfg: Dict[str, Dict], sources_cfg_path: str,
                     scenario_key: str, deployment_dir: str) -> Dict[str, Dict]:
    sources_cfg = sources_cfg[scenario_key]
    home_dir_path = user_config.get('hostHomeDir')
    kube_home_dir_path = user_config.get('kubeHostHomeDir')
    nodes_cfg = {}

    for service in sources_cfg:
        sources_cfg[service]['hostPathPrefix'] = home_dir_path
        sources_cfg[service]['vmPathPrefix'] = kube_home_dir_path
        sources_cfg[service]['deploymentDir'] = os.path.relpath(
            deployment_dir, home_dir_path)

        service_dir_path = os.path.join(deployment_dir, service)
        os.mkdir(service_dir_path)

        nodes_cfg[service] = {}
        service_nodes_cfg = generate_nodes_config(sources_cfg, service,
                                                  home_dir_path,
                                                  deployment_dir,
                                                  nodes_cfg)
        sources_cfg[service]['deployFromSources']['nodes'] = service_nodes_cfg

    sources_cfg = {scenario_key: sources_cfg}

    yaml_utils.dump_yaml(sources_cfg, sources_cfg_path)

    return nodes_cfg
