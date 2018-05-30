#!/usr/bin/env python3

import yaml
import argparse
import os
import time
import shutil


OZ_SOURCES = ['oz-worker', 'oz-panel', 'cluster-manager']
OP_SOURCES = ['op-worker', 'op-panel', 'cluster-manager']
OVERLAY_CFG = 'overlay.config'

parser = argparse.ArgumentParser(
    prog='parse sources',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)

parser.add_argument(
    type=str,
    dest='deployment_dir',
    help='path to deployment directory')

args = parser.parse_args()


def main():
    with open(os.path.join(args.deployment_dir, 'deployment_data.yml')) as deployment_data:

        # hostname looks like: [helm deployment name]-[service name]-[number]
        hostname = os.environ.get("HOSTNAME")

        split_hostname = hostname.split('-')

        # service name can have 2 parts (e.g. oneprovider-krakow)
        service_name = '-'.join(split_hostname[1:-1])

        # in our configs we number nodes from 1, k8s number pods from 0
        node_num = int(split_hostname[-1]) + 1
        node_name = 'n{}'.format(node_num)

        print("Parsing sources for node {} of {}".format(node_num,
                                                         service_name))

        sources = OZ_SOURCES if 'zone' in service_name else OP_SOURCES

        # change names of directories created by chart
        rename_pod_data_dirs(sources, service_name, node_name)

        # now copy data dirs to appropriate directories
        copy_data_dirs(yaml.load(deployment_data), hostname, service_name,
                       node_name, node_num)


def rename_pod_data_dirs(sources, service_name, node_name):
    print("Moving directories for services")
    for source in sources:
        created_path = os.path.join(args.deployment_dir, service_name, source)
        os.makedirs(created_path)
        new_path = os.path.join(args.deployment_dir, service_name,
                                '{}-{}'.format(source, node_name))
        print("Moving directory {} to {}".format(created_path, new_path))
        shutil.move(created_path, new_path)


def copy_data_dirs(deployment_data, hostname, service_name, node_name,
                   node_num):
    # have to know where to move overlay_config
    panel_from_sources = False

    hostname = '{}-{}'.format('-'.join(hostname.split('-')[:-1]), node_num)

    sources = deployment_data.get('sources').get(hostname)
    overlay_cfg = os.path.join(args.deployment_dir, service_name,
                               '{}-{}'.format(node_name, OVERLAY_CFG))

    print("Copying data dirs for sources: {}".format(sources))
    for source, source_path in sources.items():
        rel_dir = '{}-{}-{}-rel'.format(service_name, node_name, source)
        rel_dir = os.path.join(args.deployment_dir, service_name, rel_dir)

        dest_path = os.path.join(args.deployment_dir, service_name,
                                 '{}-{}'.format(source, node_name),
                                 source.replace('-', '_'))

        print("DEBUG:")
        print(os.listdir(os.path.join(args.deployment_dir, service_name,
                                 '{}-{}'.format(source, node_name))))

        print("Copying data dirs from {} to {}".format(rel_dir, dest_path))
        shutil.copytree(rel_dir, dest_path, symlinks=True)

        if 'panel' in source:
            dest_path = os.path.join(dest_path, 'etc/{}'.format(OVERLAY_CFG))
            print("Moving overlay_config from {} to {}".format(overlay_cfg,
                                                               dest_path))
            shutil.move(overlay_cfg, dest_path)
            panel_from_sources = True
            with open('onepanel_override', 'w') as f:
                f.write(source_path)

    if not panel_from_sources:
        etc = '/etc/{}/{}'.format(
            'oz_panel' if 'onezone' in service_name else 'op_panel',
             OVERLAY_CFG)
        print("Moving overlay_config from {} to {}".format(overlay_cfg, etc))
        shutil.copy(overlay_cfg, etc)


main()
