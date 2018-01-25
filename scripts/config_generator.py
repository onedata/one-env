#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from config import readers, writers
from environment import application, node
import os
import argparse
import user_config
import binaries
import time


def onezone_apps():
    return {'oz-panel', 'cluster-manager', 'oz-worker'}


def oneprovider_apps():
    return {'op-panel', 'cluster-manager', 'op-worker'}


def generate_new_nodes_config(scenario_cfg, service, host_home_dir,
                              service_dir_path, env_config_dir_path):
    new_nodes_config = []

    if 'onezone' in service:
        service_apps = onezone_apps()
    else:
        service_apps = oneprovider_apps()

    for node_config in scenario_cfg[service]['nodes']:
        node_apps = []
        node_binaries_conf = []
        for app_name in service_apps:
            app_config = {'name': app_name}

            if app_name in [a['name'] for a in node_config['binaries']]:
                app_config['hostPath'] = os.path.relpath(
                    os.path.abspath(binaries.locate(app_name)),
                    host_home_dir)
            else:
                app_config['hostPath'] = ''

            node_apps.append(application.Application(
                app_name, node_config['name'], app_config['hostPath'],
                None, service, service_dir_path, host_home_dir
            ))

            node_binaries_conf.append(app_config)

        node.create_node_config_file(env_config_dir_path, service,
                                     node_config['name'], node_apps)
        new_nodes_config.append(
            {'name': node_config['name'], 'binaries': node_binaries_conf})

    return new_nodes_config


def generate_config_for_installation(bin_cfg, bin_cfg_path, scenario_key,
                                     env_config_dir_path):
    scenario_cfg = bin_cfg[scenario_key]
    host_home_dir = user_config.get('hostHomeDir')
    kube_host_home_dir = user_config.get('kubeHostHomeDir')

    for service in scenario_cfg:
        scenario_cfg[service]['hostPathPrefix'] = host_home_dir
        scenario_cfg[service]['vmPathPrefix'] = kube_host_home_dir
        scenario_cfg[service]['deploymentDir'] = os.path.relpath(
            env_config_dir_path, host_home_dir)

        service_dir_path = os.path.join(env_config_dir_path, service)
        os.mkdir(service_dir_path)

        bin_cfg[scenario_key][service]['nodes'] = \
            generate_new_nodes_config(scenario_cfg, service, host_home_dir,
                                      service_dir_path, env_config_dir_path)

    writer = writers.ConfigWriter(bin_cfg, 'yaml')
    with open(bin_cfg_path, 'w') as f:
        f.write(writer.dump())


def generate_config_for_single_service(cfg):
    config_nodes = cfg['nodes']
    # TODO: After merge prefix will not be in this place
    prefix = cfg['hostPathPrefix']
    apps = []
    nodes = []

    # FIXME:
    for n in config_nodes:
        service = ''
        for app in n['binaries']:
            if app['name'] == 'oz-panel':
                service = 'onezone'
                break
            if app['name'] == 'op-panel':
                service = 'oneprovider'
                break

        for app in n['binaries']:
            project_path = app.get('hostPath', None)
            project_path = os.path.join(prefix, project_path) \
                if project_path else None
            apps.append(application.Application(
                app['name'], n['name'], project_path,
                app.get('additionalArgs', None),
                service
            ))

        nodes.append(
            node.Node(n['name'], apps, args, service))
        apps = []


def generate_configs(bin_cfg, bin_cfg_path, env_config_dir_path,
                     scenario_key):
    if scenario_key:
        generate_config_for_installation(bin_cfg, bin_cfg_path, scenario_key,
                                         env_config_dir_path)
    else:
        generate_config_for_single_service(bin_cfg)


parser = argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    description='Bring up onedata environment.')


parser.add_argument(
    '-c', '--cfg_path',
    action='store',
    help='path to environment configuration file',
    dest='cfg_path')

parser.add_argument(
    '-o', '--out_dir',
    action='store',
    help='path to dir where configs should be written',
    default=os.getcwd(),
    dest='out_dir')

parser.add_argument(
    '-s', '--scenario',
    action='store',
    help='',
    default='',
    dest='scenario')


if __name__ == '__main__':
    args = parser.parse_args()

    generate_configs(args.scenario, args.out_dir, args.cfg_path)


