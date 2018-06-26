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


ROOT_PATH = '/'


def onezone_apps():
    return {APP_OZ_PANEL, APP_CLUSTER_MANAGER, APP_ONEZONE}


def oneprovider_apps():
    return {APP_OP_PANEL, APP_CLUSTER_MANAGER, APP_ONEPROVIDER}


def generate_app_config(app_name, node_name, node_config, service,
                        service_dir_path, host_home_dir, node_apps,
                        node_sources_conf, scenario_sources_cfg):
    override_prefix = False
    app_config = {'name': app_name}

    if app_name in [a['name'] for a in node_config.get('sources', [])]:
        source_path = os.path.abspath(sources.locate(app_name,
                                                     service, node_name))

        if source_path.startswith('/home'):
            app_config['hostPath'] = os.path.relpath(source_path, host_home_dir)
        else:
            override_prefix = True
            host_home_dir = ROOT_PATH
            app_config['hostPath'] = source_path

        for app in scenario_sources_cfg[service]['sources']:
            if 'hostPath' not in app and app['name'] == app_name:
                app['hostPath'] = app_config['hostPath']

    else:
        app_config['hostPath'] = ''

    node_apps.append(application.Application(
        app_name, node_name, app_config['hostPath'],
        None, service, service_dir_path, host_home_dir
    ))

    node_sources_conf.append(app_config)

    return override_prefix


def generate_nodes_config(scenario_sources_cfg, service, host_home_dir,
                          service_dir_path, env_config_dir_path):
    new_nodes_config = {}
    override_prefix = False

    if 'onezone' in service:
        service_apps = onezone_apps()
    else:
        service_apps = oneprovider_apps()

    for node_name, node_config in scenario_sources_cfg[service]['nodes'].items():
        node_apps = []
        node_sources_conf = []
        for app_name in service_apps:
            if generate_app_config(app_name, node_name, node_config, service,
                                   service_dir_path, host_home_dir, node_apps,
                                   node_sources_conf, scenario_sources_cfg):
                override_prefix = True

        node.change_node_app_config(env_config_dir_path, service,
                                    node_name, node_apps)
        new_nodes_config[node_name] = {'sources': node_sources_conf}

    if override_prefix:
        # not using ROOT_PATH here cause in charts we use '/' in path
        # concatenation so it will be appended there
        scenario_sources_cfg[service]['hostPathPrefix'] = ''
        scenario_sources_cfg[service]['vmPathPrefix'] = ''
        scenario_sources_cfg[service]['deploymentDir'] = os.path.relpath(
            env_config_dir_path, ROOT_PATH)

    return new_nodes_config


def generate_configs(sources_cfg, sources_cfg_path, scenario_key,
                     deployment_dir):
    scenario_sources_cfg = sources_cfg[scenario_key]
    host_home_dir = user_config.get('hostHomeDir')
    kube_host_home_dir = user_config.get('kubeHostHomeDir')

    for service in scenario_sources_cfg:
        scenario_sources_cfg[service]['hostPathPrefix'] = host_home_dir
        scenario_sources_cfg[service]['vmPathPrefix'] = kube_host_home_dir
        scenario_sources_cfg[service]['deploymentDir'] = os.path.relpath(
            deployment_dir, host_home_dir)

        service_dir_path = os.path.join(deployment_dir, service)
        os.mkdir(service_dir_path)

        scenario_sources_cfg[service]['nodes'] = \
            generate_nodes_config(scenario_sources_cfg, service,
                                  host_home_dir, service_dir_path,
                                  deployment_dir)

    writer = writers.ConfigWriter(sources_cfg, 'yaml')
    with open(sources_cfg_path, 'w') as f:
        f.write(writer.dump())
