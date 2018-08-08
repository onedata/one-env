"""
Part of onenv tool that allows to gather all logs and relevant data from current
deployment and place them in desired location.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"


import os
import shutil
import argparse

import cmd
import pods
import helm
import console
import sources
import user_config
import argparse_utils
import deployments_dir
from names_and_paths import *

SCRIPT_DESCRIPTION = 'Gathers all logs and relevant data from current ' \
                     'deployment and places them in desired location.'

STATEFUL_SET_OUTPUT_FILE = 'stateful-set.txt'

POD_LOGS_DIR = 'pod-logs'

parser = argparse.ArgumentParser(
    prog='onenv wait',
    formatter_class=argparse_utils.ArgumentsHelpFormatter,
    description=SCRIPT_DESCRIPTION
)

parser.add_argument(
    type=str,
    nargs='?',
    action='store',
    help='directory where deployment data should be stored - if not specified, '
         'it will be placed in deployments dir '
         '(~/.one-env/deployments/<timestamp>)',
    dest='path')

user_config.ensure_exists()
helm.ensure_deployment(exists=True, fail_with_error=True)

args = parser.parse_args()


def onezone_apps():
    return {APP_OZ_PANEL, APP_CLUSTER_MANAGER, APP_ONEZONE}


def oneprovider_apps():
    return {APP_OP_PANEL, APP_CLUSTER_MANAGER, APP_ONEPROVIDER}


def copytree_no_overwrite(src, dst):
    if not os.path.isdir(dst):
        os.mkdir(dst)
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.islink(s):
            pass
        elif os.path.isdir(s):
            copytree_no_overwrite(s, d)
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
    this_pod_logs_dir = os.path.join(pod_logs_dir, pods.get_name(pod))
    try:
        os.mkdir(this_pod_logs_dir)
    except FileExistsError:
        pass
    with open(os.path.join(this_pod_logs_dir, 'entrypoint.log'), 'w+') as f:
        f.write(pods.pod_logs(pod))

    service_type = pods.get_service_type(pod).lower()

    if 'onezone' in service_type:
        service_apps = onezone_apps()
    elif 'oneprovider' in service_type:
        service_apps = oneprovider_apps()
    else:
        continue

    for app in service_apps:
        app_dir = os.path.join(this_pod_logs_dir, app)
        pod_name = pods.get_name(pod)
        log_dir = cmd.check_output(
            pods.cmd_exec(pod_name, ['bash', '-c', 'readlink -f {}'.format(
                sources.logs_dir(app, pod))]))

        if os.path.exists(app_dir):
            console.warning('Path {} already exists, it will be '
                            'deleted'.format(app_dir))
            shutil.rmtree(app_dir)

        cmd.call(pods.cmd_copy_from_pod('{}:{}'.format(pod_name, log_dir),
                                        app_dir))


# If requested, copy it to an output location
if args.path:
    if os.path.isdir(args.path):
        console.warning(
            'Directory {} exists, exporting anyway.'.format(args.path))

    if os.path.isfile(args.path):
        console.warning('File {} exists, overwriting.'.format(args.path))
        os.remove(args.path)

    copytree_no_overwrite(deployment_path, args.path)
else:
    console.info('Deployment data was placed in {}'.format(deployment_path))
