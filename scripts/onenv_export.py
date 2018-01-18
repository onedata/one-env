"""
Part of onenv tool that allows to gather all logs and relevant data from current
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
import helm
import deployments_dir
import console

SCRIPT_DESCRIPTION = 'Gathers all logs and relevant data from current ' \
                     'deployment and places them in desired location.'

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
    default=argparse.SUPPRESS,
    help='directory where deployment data should be stored - if not specified, '
         'it will be placed in deployments dir '
         '(~/.one-env/deployments/<timestamp>)',
    dest='path')

helm.ensure_deployment(exists=True, fail_with_error=True)

args = parser.parse_args()


def copytree_no_overwrite(src, dst):
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            if os.path.isdir(d):
                copytree_no_overwrite(s, d)
            else:
                shutil.copytree(s, d)
        else:
            shutil.copy2(s, d)


# Accumulate all the data in deployment dir
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

# If requested, copy it to an output location
if 'path' in args:
    if os.path.isdir(args.path):
        console.warning(
            'Directory {} exists, exporting anyway.'.format(args.path))

    if os.path.isfile(args.path):
        console.warning('File {} exists, overwriting.'.format(args.path))
        os.remove(args.path)

    copytree_no_overwrite(deployment_path, args.path)
else:
    console.info('Deployment data was placed in {}'.format(deployment_path))
