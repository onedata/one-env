"""
Part of onenv tool that allows to gather all logs and data from current
deployment and place them in desired location.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import argparse
import shutil
import os
import pods
import deployments_dir
import console

SCRIPT_DESCRIPTION = 'Gathers all logs and data from current deployment and' \
                     'places them in desired location.'

STATEFUL_SET_OUTPUT_FILE = 'stateful-set.txt'

POD_LOGS_DIR = 'pod-logs'

parser = argparse.ArgumentParser(
    prog='onenv wait',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    description=SCRIPT_DESCRIPTION
)

parser.add_argument(
    type=str,
    nargs='?',
    action='store',
    default='./onenv-deployment',
    help='directory where deployment data should be stored',
    dest='path')

args = parser.parse_args()

if os.path.isdir(args.path):
    console.warning('Directory {} exists, overwriting.'.format(args.path))
    shutil.rmtree(args.path)

if os.path.isfile(args.path):
    console.warning('File {} exists, overwriting.'.format(args.path))
    os.remove(args.path)

deployment_path = deployments_dir.current_deployment_dir()

with open(os.path.join(deployment_path, STATEFUL_SET_OUTPUT_FILE), 'w+') as f:
    f.write(pods.describe_stateful_set())

pod_logs_dir = os.path.join(deployment_path, POD_LOGS_DIR)
try:
    os.mkdir(pod_logs_dir)
except FileExistsError:
    pass

for pod in pods.list_pods():
    this_pod_logs_dir = os.path.join(pod_logs_dir, pod)
    try:
        os.mkdir(this_pod_logs_dir)
    except FileExistsError:
        pass
    with open(os.path.join(this_pod_logs_dir, 'entrypoint.log'), 'w+') as f:
        f.write(pods.logs(pod))

shutil.copytree(deployment_path, args.path)
