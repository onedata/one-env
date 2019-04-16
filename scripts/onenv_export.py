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
import subprocess
from contextlib import suppress
from typing import List, Optional

from kubernetes.client import V1Pod

from .utils.k8s import pods, helm
from .utils.terminal import warning
from .utils.yaml_utils import dump_yaml
from .utils.deployment import sources_paths
from .utils.common import force_create_directory
from .utils import shell, terminal, arg_help_formatter
from .utils.one_env_dir import user_config, deployments_dir
from .utils.names_and_paths import (SERVICE_ONEZONE, SERVICE_ONEPROVIDER,
                                    ONEZONE_APPS, ONEPROVIDER_APPS,
                                    SERVICE_ONECLIENT)


STATEFUL_SET_OUTPUT_FILE = 'stateful-set.txt'
POD_LOGS_DIR = 'pod-logs'
ONECLIENT_LOGS_DIR = 'oneclient_logs'


def copytree_no_overwrite(src: str, dst: str) -> None:
    if not os.path.isdir(dst):
        os.mkdir(dst)
    for item in os.listdir(src):
        item_src_path = os.path.join(src, item)
        item_dst_path = os.path.join(dst, item)
        if os.path.islink(item_src_path):
            pass
        elif os.path.isdir(item_src_path):
            copytree_no_overwrite(item_src_path, item_dst_path)
        else:
            shutil.copy2(item_src_path, item_dst_path)


def get_pod_logs_dir(deployment_path: str) -> str:
    pod_logs_dir = os.path.join(deployment_path, POD_LOGS_DIR)
    with suppress(FileExistsError):
        os.mkdir(pod_logs_dir)
    return pod_logs_dir


def copy_logs(path: str, pod_logs_dir: str) -> None:
    if os.path.isdir(path):
        terminal.warning('Directory {} exists, exporting '
                         'anyway.'.format(path))

    if os.path.isfile(path):
        terminal.warning('File {} exists, overwriting.'.format(path))
        os.remove(path)

    copytree_no_overwrite(pod_logs_dir, path)


def export_command_logs(command: List[str], pod_logs_dir: str,
                        logfile_name: str, append: bool = False, ) -> None:
    command_logfile_path = os.path.join(pod_logs_dir, logfile_name)
    mode = 'a' if append else 'w'

    try:
        with open(command_logfile_path, mode) as command_logfile:
            subprocess.call(command, stdout=command_logfile,
                            stderr=command_logfile)
    except subprocess.CalledProcessError:
        print('Error during exporting logs for command: {}. '
              'See {} for more details.'.format(command, command_logfile_path))


def export_oc_logs(client_log_dir: str, this_pod_logs_dir: str, pod: V1Pod):
    pod_name = pods.get_name(pod)
    oneclient_logs_dir = os.path.join(this_pod_logs_dir, ONECLIENT_LOGS_DIR)
    force_create_directory(oneclient_logs_dir)

    try:
        subprocess.call(pods.rsync_cmd('{}:{}'.format(pod_name,
                                                      client_log_dir),
                                       oneclient_logs_dir))
    except subprocess.CalledProcessError as ex:
        warning('Couldn\'t get logs for oneclient from {} pod.\n'
                'Reason: {}'.format(pod, ex.output))


def export_oz_op_logs(service_apps: List[str], this_pod_logs_dir: str,
                      pod: V1Pod) -> None:
    for app in service_apps:
        app_dir = os.path.join(this_pod_logs_dir, app)
        pod_name = pods.get_name(pod)

        try:
            log_dir = shell.check_output(
                pods.exec_cmd(pod_name,
                              ['bash', '-c', 'readlink -f {}'.format(
                                  sources_paths.get_logs_dir(app, pod_name))]))

            force_create_directory(app_dir)

            subprocess.call(
                pods.rsync_cmd('{}:{}'.format(pod_name, log_dir),
                               app_dir))
        except subprocess.CalledProcessError as ex:
            warning('Couldn\'t get logs for application {} in {} pod.\n'
                    'Reason: {}'.format(app, pod_name, ex.output))


def export_pod_logs(pod: V1Pod, pod_logs_dir: str,
                    pods_list: List[V1Pod],
                    client_log_dir: str) -> Optional[str]:
    image = None
    pod_name = pods.get_name(pod)
    service_type = pods.get_service_type(pod)
    if service_type:
        service_type = service_type.lower()

    this_pod_logs_dir = os.path.join(pod_logs_dir, pod_name)
    with suppress(FileExistsError):
        os.mkdir(this_pod_logs_dir)
    entrypoint_logfile_path = os.path.join(this_pod_logs_dir,
                                           'entrypoint.log')
    with open(entrypoint_logfile_path, 'w+') as f:
        try:
            entrypoint_logs = pods.pod_logs(pod, stderr=f,
                                            container=service_type)
            f.write(entrypoint_logs)
        except subprocess.CalledProcessError:
            warning('Couldn\'t get entrypoint logs for pod {}. See {} for '
                    'more details'.format(pod_name, entrypoint_logfile_path))

    if pod in pods_list and service_type:
        if SERVICE_ONEZONE in service_type:
            service_apps = ONEZONE_APPS
            export_oz_op_logs(service_apps, this_pod_logs_dir, pod)
        elif SERVICE_ONEPROVIDER in service_type:
            service_apps = ONEPROVIDER_APPS
            export_oz_op_logs(service_apps, this_pod_logs_dir, pod)
        elif SERVICE_ONECLIENT in service_type:
            export_oc_logs(client_log_dir, this_pod_logs_dir, pod)
        image = pods.get_container_image(service_type, pod)

    return image


def export_logs(path: str, client_log_dir: str) -> None:
    # Accumulate all the data in one_env dir
    deployment_path = deployments_dir.get_current_deployment_dir()

    with open(os.path.join(deployment_path, STATEFUL_SET_OUTPUT_FILE),
              'w+') as f:
        f.write(pods.describe_stateful_set())

    pod_logs_dir = get_pod_logs_dir(deployment_path)

    export_command_logs(pods.get_pods_cmd(), pod_logs_dir, 'k8s_get_pods.log')
    export_command_logs(pods.get_pods_cmd(output='yaml'), pod_logs_dir,
                        'k8s_get_pods.log', append=True)
    export_command_logs(pods.describe_pods_cmd(), pod_logs_dir,
                        'k8s_describe_pods.log')

    images = {}
    pods_list = pods.list_pods()
    for pod in pods.list_pods_and_jobs():
        pod_image = export_pod_logs(pod, pod_logs_dir, pods_list,
                                    client_log_dir)
        if pod_image:
            images[pods.get_name(pod)] = pod_image

    dump_yaml(images, os.path.join(pod_logs_dir, 'images.yaml'))

    # If requested, copy it to an output location
    if path:
        copy_logs(path, pod_logs_dir)
    else:
        terminal.info('Deployment data was placed in {}'
                      .format(deployment_path))


def main() -> None:
    export_args_parser = argparse.ArgumentParser(
        prog='onenv export',
        formatter_class=arg_help_formatter.ArgumentsHelpFormatter,
        description='Gathers all logs and relevant data from current '
                    'deployment and places them in desired location.'
    )

    export_args_parser.add_argument(
        nargs='?',
        help='Directory where deployment data should be stored - if not '
             'specified, it will be placed in deployments dir '
             '(~/.one-env/deployments/<timestamp>)',
        dest='path'
    )

    export_args_parser.add_argument(
        '-c', '--client-log-dir',
        help='Path where script should look for oneclient logs files',
        dest='client_log_dir',
        default='/tmp/oneclient'
    )

    export_args = export_args_parser.parse_args()

    user_config.ensure_exists()
    helm.ensure_deployment(exists=True, fail_with_error=True)

    export_logs(export_args.path, export_args.client_log_dir)


if __name__ == '__main__':
    main()
