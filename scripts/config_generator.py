"""
Generates overlay configs based on given binaries configuration.
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
import binaries
import time


def providers_mapping(name):
    return {'oneprovider-krakow': 'oneprovider-p1',
            'oneprovider-paris': 'oneprovider-p2',
            'oneprovider-p1': 'oneprovider-krakow',
            'oneprovider-p2': 'oneprovider-paris'}.get(name, name)

def onezone_apps():
    return {'oz-panel', 'cluster-manager', 'oz-worker'}


def oneprovider_apps():
    return {'op-panel', 'cluster-manager', 'op-worker'}


def generate_app_config(app_name, node_name, node_config, service,
                        service_dir_path, host_home_dir, node_apps,
                        node_binaries_conf, custom_node_bin_cfg):
    app_config = {'name': app_name}

    if app_name in [a for a in custom_node_bin_cfg]:
        app_config['hostPath'] = os.path.relpath(
            os.path.abspath(binaries.locate(app_name)),
            host_home_dir)
    else:
        app_config['hostPath'] = ''

    node_apps.append(application.Application(
        app_name, node_name, app_config['hostPath'],
        None, service, service_dir_path, host_home_dir
    ))

    node_binaries_conf.append(app_config)


def generate_new_nodes_config(scenario_cfg, service, host_home_dir,
                              service_dir_path, env_config_dir_path,
                              custom_service_bin_cfg):
    new_nodes_config = {}

    if 'onezone' in service:
        service_apps = onezone_apps()
    else:
        service_apps = oneprovider_apps()

    for node_name, node_config in scenario_cfg[service]['nodes'].items():
        node_apps = []
        node_binaries_conf = []
        for app_name in service_apps:
            generate_app_config(app_name, node_name, node_config, service,
                                service_dir_path, host_home_dir, node_apps,
                                node_binaries_conf, custom_service_bin_cfg.get(node_name))

        node.create_node_config_file(env_config_dir_path, service,
                                     node_name, node_apps)
        new_nodes_config[node_name] = {'binaries': node_binaries_conf}

    return new_nodes_config


def generate_configs(bin_cfg, bin_cfg_path, scenario_key, env_config_dir_path,
                     env_cfg):
    scenario_cfg = bin_cfg[scenario_key]
    host_home_dir = user_config.get('hostHomeDir')
    kube_host_home_dir = user_config.get('kubeHostHomeDir')
    custom_bin_cfg = env_cfg.get('binaries')

    for service in scenario_cfg:
        scenario_cfg[service]['hostPathPrefix'] = host_home_dir
        scenario_cfg[service]['vmPathPrefix'] = kube_host_home_dir
        scenario_cfg[service]['deploymentDir'] = os.path.relpath(
            env_config_dir_path, host_home_dir)

        service_dir_path = os.path.join(env_config_dir_path, service)
        os.mkdir(service_dir_path)

        bin_cfg[scenario_key][service]['nodes'] = \
            generate_new_nodes_config(scenario_cfg, service, host_home_dir,
                                      service_dir_path, env_config_dir_path,
                                      custom_bin_cfg.get(providers_mapping(service)))

    writer = writers.ConfigWriter(bin_cfg, 'yaml')
    with open(bin_cfg_path, 'w') as f:
        f.write(writer.dump())
