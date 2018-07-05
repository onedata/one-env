"""
Part of onenv tool that allows to
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


import pods
import deployments_dir



SCRIPT_DESCRIPTION = 'Rsync local directory with directory in pod'

parser = argparse.ArgumentParser(
    prog='onenv update',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    description=SCRIPT_DESCRIPTION
)

parser.add_argument(
    type=str,
    nargs='?',
    action='store',
    default=argparse.SUPPRESS,
    help='pod name (or matching pattern, use "-" for wildcard) - '
         'display detailed status of given pod.',
    dest='pod')


args = parser.parse_args()


def update_sources_in_pod(pod):
    deployment_dir = deployments_dir.current_deployment_dir()

    with open(os.path.join(deployment_dir, 'deployment_data.yml')) as \
            deployment_data_file:
        deployment_data = yaml.load(deployment_data_file)

        pod_name = pods.get_name(pod)
        pod_cfg = deployment_data.get('sources').get(pod_name).items()

        for source, source_path in pod_cfg:
            build_path = os.path.join(source_path, '_build')
            destination_path = '{}:{}'.format(pod_name, source_path)
            subprocess.call(pods.cmd_rsync(build_path, destination_path),
                            shell=True)


def main():

    if args.pod:
        pods.match_pod_and_run(args.pod, update_sources_in_pod)


if __name__ == "__main__":
    main()
