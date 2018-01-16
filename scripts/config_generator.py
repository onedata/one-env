#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from config import readers, writers
from environment import application, node
import os
import argparse
import user_config
import binaries
import time


def generate_config_for_installation(cfg, scenario_key, cfg_path,
                                     deployment_dir):
    scenario_cfg = cfg[scenario_key]
    host_home_dir = user_config.get('hostHomeDir')
    kube_host_home_dir = user_config.get('kubeHostHomeDir')

    for service in scenario_cfg:
        scenario_cfg[service]['hostPathPrefix'] = host_home_dir
        scenario_cfg[service]['vmPathPrefix'] = kube_host_home_dir
        scenario_cfg[service]['deploymentDir'] = os.path.relpath(
            deployment_dir, host_home_dir)

        service_dir_path = os.path.join(deployment_dir, service)
        os.mkdir(service_dir_path)

        config_nodes = scenario_cfg[service]['nodes']
        apps = []
        nodes = []

        for n in config_nodes:
            for app in n['binaries']:
                app['hostPath'] = os.path.relpath(
                    os.path.abspath(binaries.locate(app['name'])),
                    host_home_dir)
                apps.append(application.Application(
                    app['name'], n['name'],
                    os.path.join(host_home_dir, app['hostPath']),
                    app.get('additionalArgs', None), service, service_dir_path
                ))

            nodes.append(node.Node(n['name'], apps, service, deployment_dir))
            apps = []

    writer = writers.ConfigWriter(cfg, 'yaml')
    with open(cfg_path, 'w') as f:
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


def generate_configs(scenario_path, deployment_dir, cfg_path):
    # create yaml or json reader and read data
    reader = readers.ConfigReader(cfg_path)
    env_cfg = reader.load()

    r = readers.ConfigReader(os.path.join(scenario_path, 'requirements.yaml'))
    requirements = r.load()

    scenario_key = ""

    for req in requirements.get('dependencies'):
        for tag in req.get('tags', []):
            if 'bin-vals' in tag:
                scenario_key = req.get('name')

    if scenario_key:
        generate_config_for_installation(env_cfg, scenario_key,
                                         cfg_path, deployment_dir)
    else:
        generate_config_for_single_service(env_cfg)


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


