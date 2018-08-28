"""
Generates overlay configs based on given sources configuration.
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"


from config import readers, writers
from environment import application, node
import os
import user_config
import sources
from names_and_paths import *


ROOT_PATH = '/'


def onezone_apps():
    return {APP_OZ_PANEL, APP_CLUSTER_MANAGER, APP_ONEZONE}


def oneprovider_apps():
    return {APP_OP_PANEL, APP_CLUSTER_MANAGER, APP_ONEPROVIDER}


def generate_app_config(app_name, node_name, node_config, service,
                        service_dir_path, host_home_dir, node_apps,
                        node_sources_conf, deploy_from_sources):
    override_prefix = False
    app_config = {'name': app_name}

    if (deploy_from_sources and
            app_name in [a['name'] for a in node_config.get('sources', [])]):
        source_path = os.path.abspath(sources.locate(app_name,
                                                     service, node_name))

        if source_path.startswith('/home'):
            app_config['hostPath'] = os.path.relpath(source_path, host_home_dir)
        else:
            override_prefix = True
            host_home_dir = ROOT_PATH
            app_config['hostPath'] = source_path

    else:
        app_config['hostPath'] = ''

    node_apps.append(application.Application(
        app_name, node_name, app_config['hostPath'],
        None, service, service_dir_path, host_home_dir
    ))

    node_sources_conf.append(app_config)

    return override_prefix


def generate_nodes_config(scenario_sources_cfg, service, host_home_dir,
                          service_dir_path, env_config_dir_path, nodes_cfg):
    new_nodes_config = {}
    override_prefix = False

    if 'onezone' in service:
        service_apps = onezone_apps()
    else:
        service_apps = oneprovider_apps()

    for node_name, node_config in scenario_sources_cfg[service]['deployFromSources']['nodes'].items():
        node_apps = []
        node_sources_conf = []
        deploy_from_sources = scenario_sources_cfg[service]['deployFromSources']['enabled']
        for app_name in service_apps:
            if generate_app_config(app_name, node_name, node_config, service,
                                   service_dir_path, host_home_dir, node_apps,
                                   node_sources_conf, deploy_from_sources):
                override_prefix = True

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


def generate_configs(sources_cfg: dict, sources_cfg_path: str,
                     scenario_key: str, deployment_dir: str):
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
                                                  service_dir_path,
                                                  deployment_dir,
                                                  nodes_cfg)
        sources_cfg[service]['deployFromSources']['nodes'] = service_nodes_cfg

    sources_cfg = {scenario_key: sources_cfg}

    writer = writers.ConfigWriter(sources_cfg, 'yaml')
    with open(sources_cfg_path, 'w') as f:
        f.write(writer.dump())

    return nodes_cfg
