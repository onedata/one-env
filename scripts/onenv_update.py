"""
Part of onenv tool that allows to update sources in given pod.
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import os
import yaml
import console
import argparse
import subprocess

import argparse_utils
import pods
import deployments_dir


SCRIPT_DESCRIPTION = 'Update sources in given pod.'

parser = argparse.ArgumentParser(
    prog='onenv update',
    formatter_class=argparse_utils.ArgumentsHelpFormatter,
    description=SCRIPT_DESCRIPTION
)

parser.add_argument(
    type=str,
    nargs='?',
    action='store',
    help='Pod name (or matching pattern, use "-" for wildcard).'
         'If not specified whole deployment will be updated.',
    dest='pod')


args = parser.parse_args()


def update_sources_for_component(pod_name, source_path):
    build_path = os.path.join(source_path, '_build')
    destination_path = '{}:{}'.format(pod_name, source_path)

    subprocess.call(pods.cmd_rsync(build_path, destination_path),
                    shell=True)


def update_sources_in_pod(pod):
    deployment_dir = deployments_dir.current_deployment_dir()

    try:
        with open(os.path.join(deployment_dir, 'deployment_data.yml')) as \
                deployment_data_file:
            deployment_data = yaml.load(deployment_data_file)

            pod_name = pods.get_name(pod)
            pod_cfg = deployment_data.get('sources').get(pod_name)

            if pod_cfg:
                for source, source_path in pod_cfg.items():
                    update_sources_for_component(pod_name, source_path)
    except FileNotFoundError:
        console.error('File {} containing deployment data not found. '
                      'Is service started from sources?')


def update_deployment():
    pods_list = pods.list_pods()
    for pod in pods_list:
        update_sources_in_pod(pod)


def main():
    if args.pod:
        pods.match_pod_and_run(args.pod, update_sources_in_pod)
    else:
        update_deployment()


if __name__ == "__main__":
    main()
