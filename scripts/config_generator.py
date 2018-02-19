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
import argparse
import user_config
import sources
import time
import sys
from names_and_paths import *


def onezone_apps():
    return {APP_OZ_PANEL, APP_CLUSTER_MANAGER, APP_ONEZONE}


def oneprovider_apps():
    return {APP_OP_PANEL, APP_CLUSTER_MANAGER, APP_ONEPROVIDER}


def generate_app_config(app_name, node_name, node_config, service,
                        service_dir_path, host_home_dir, node_apps,
                        node_sources_conf):
    app_config = {'name': app_name}

    if app_name in [a['name'] for a in node_config.get('sources', [])]:
        app_config['hostPath'] = os.path.relpath(
            os.path.abspath(sources.locate(app_name, service, node_name)),
            host_home_dir)
    else:
        app_config['hostPath'] = ''

    node_apps.append(application.Application(
        app_name, node_name, app_config['hostPath'],
        None, service, service_dir_path, host_home_dir
    ))

    node_sources_conf.append(app_config)


def generate_new_nodes_config(scenario_cfg, service, host_home_dir,
                              service_dir_path, env_config_dir_path):
    new_nodes_config = {}

    if 'onezone' in service:
        service_apps = onezone_apps()
    else:
        service_apps = oneprovider_apps()

    for node_name, node_config in scenario_cfg[service]['nodes'].items():
        node_apps = []
        node_sources_conf = []
        for app_name in service_apps:
            generate_app_config(app_name, node_name, node_config, service,
                                service_dir_path, host_home_dir, node_apps,
                                node_sources_conf)

        node.create_node_config_file(env_config_dir_path, service,
                                     node_name, node_apps)
        new_nodes_config[node_name] = {'sources': node_sources_conf}

    return new_nodes_config


def generate_configs(sources_cfg, sources_cfg_path, scenario_key, env_config_dir_path):
    scenario_cfg = sources_cfg[scenario_key]
    host_home_dir = user_config.get('hostHomeDir')
    kube_host_home_dir = user_config.get('kubeHostHomeDir')

    for service in scenario_cfg:
        scenario_cfg[service]['hostPathPrefix'] = host_home_dir
        scenario_cfg[service]['vmPathPrefix'] = kube_host_home_dir
        scenario_cfg[service]['deploymentDir'] = os.path.relpath(
            env_config_dir_path, host_home_dir)

        service_dir_path = os.path.join(env_config_dir_path, service)
        os.mkdir(service_dir_path)

        sources_cfg[scenario_key][service]['nodes'] = \
            generate_new_nodes_config(scenario_cfg, service, host_home_dir,
                                      service_dir_path, env_config_dir_path)

    writer = writers.ConfigWriter(sources_cfg, 'yaml')
    with open(sources_cfg_path, 'w') as f:
        f.write(writer.dump())
