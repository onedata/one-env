"""
Part of onenv tool that allows to update sources in given pod.
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import os
import glob
import argparse
import subprocess
from typing import List

import kubernetes

from .utils.k8s import pods, helm
from .utils.yaml_utils import load_yaml
from .utils import terminal, arg_help_formatter
from .utils.one_env_dir import deployments_dir, user_config
from .utils.names_and_paths import (APP_OP_PANEL, APP_OZ_PANEL, APP_ONEZONE,
                                    APP_ONEPROVIDER, APP_CLUSTER_MANAGER)


GUI_DIRS_TO_SYNC = ['_build/default/rel/*/data/gui_static']
BACKEND_DIRS_TO_SYNC = ['_build/default/lib', 'src', 'include']
ALL_DIRS_TO_SYNC = GUI_DIRS_TO_SYNC + BACKEND_DIRS_TO_SYNC


def update_sources_for_component(pod_name: str, source_path: str,
                                 dirs_to_sync: List[str],
                                 delete: bool = False) -> None:
    for dir_to_sync in dirs_to_sync:
        dir_path = os.path.join(source_path, dir_to_sync)
        for expanded_path in glob.glob(dir_path):
            destination_path = '{}:{}'.format(pod_name,
                                              os.path.dirname(expanded_path))

            if os.path.exists(expanded_path):
                rsync_cmd = pods.rsync_cmd(expanded_path, destination_path,
                                           delete)
                subprocess.call(rsync_cmd, shell=True)


def update_sources_in_pod(pod: kubernetes.client.V1Pod,
                          sources_to_update: List[str],
                          dirs_to_sync: List[str],
                          delete: bool = False) -> None:
    deployment_dir = deployments_dir.get_current_deployment_dir()
    deployment_data_path = os.path.join(deployment_dir, 'deployment_data.yml')
    try:
        deployment_data = load_yaml(deployment_data_path)
    except FileNotFoundError:
        terminal.error('File {} containing deployment data not found. '
                       'Is service started from sources?'
                       .format(deployment_data_path))
    else:
        pod_name = pods.get_name(pod)
        pod_cfg = deployment_data.get('sources').get(pod_name)

        if pod_cfg:
            for source_name, source_path in pod_cfg.items():
                if source_name in sources_to_update:
                    update_sources_for_component(pod_name, source_path,
                                                 dirs_to_sync, delete)


def update_deployment(sources_to_update: List[str], dirs_to_sync: List[str],
                      delete: bool = False) -> None:
    for pod in pods.list_pods():
        update_sources_in_pod(pod, sources_to_update, dirs_to_sync, delete)


def main() -> None:
    update_args_parser = argparse.ArgumentParser(
        prog='onenv update',
        formatter_class=arg_help_formatter.ArgumentsHelpFormatter,
        description='Update sources in given pod.'
    )

    update_args_parser.add_argument(
        nargs='?',
        help='Pod name (or matching pattern, use "-" for wildcard).'
             'If not specified whole deployment will be updated.',
        dest='pod'
    )

    update_args_parser.add_argument(
        '-d', '--delete',
        help='specifies if rsync should delete files in pods when they are '
             'deleted on host',
        action='store_true'
    )

    update_args_parser.add_argument(
        '-p', '--panel',
        action='store_true',
        help='update sources for onepanel service',
    )

    update_args_parser.add_argument(
        '-c', '--cluster-manager',
        action='store_true',
        help='update sources for cluster-manager service',
    )

    update_args_parser.add_argument(
        '-w', '--worker',
        action='store_true',
        help='update sources for (op|oz)-worker',
    )

    update_args_parser.add_argument(
        '-a', '--all',
        action='store_true',
        help='update sources for all services',
    )

    sources_type = update_args_parser.add_mutually_exclusive_group()

    sources_type.add_argument(
        '-g', '--gui',
        action='store_const',
        help='update sources only for GUI',
        const=GUI_DIRS_TO_SYNC,
        dest='dirs_to_sync'
    )

    sources_type.add_argument(
        '-b', '--backend',
        action='store_const',
        help='update sources only for backend',
        const=BACKEND_DIRS_TO_SYNC,
        dest='dirs_to_sync'
    )

    update_args = update_args_parser.parse_args()

    user_config.ensure_exists()
    helm.ensure_deployment(exists=True, fail_with_error=True)

    sources_to_update = []

    if update_args.panel:
        sources_to_update.extend([APP_OZ_PANEL, APP_OP_PANEL])
    if update_args.worker:
        sources_to_update.extend([APP_ONEZONE, APP_ONEPROVIDER])
    if update_args.cluster_manager:
        sources_to_update.extend([APP_CLUSTER_MANAGER])
    if update_args.all or not sources_to_update:
        sources_to_update = [APP_OZ_PANEL, APP_OP_PANEL, APP_ONEZONE,
                             APP_ONEPROVIDER, APP_CLUSTER_MANAGER]

    dirs_to_sync = update_args.dirs_to_sync or ALL_DIRS_TO_SYNC

    if update_args.pod:
        pods.match_pod_and_run(update_args.pod, update_sources_in_pod,
                               sources_to_update, dirs_to_sync,
                               update_args.delete)
    else:
        update_deployment(sources_to_update, dirs_to_sync, update_args.delete)


if __name__ == '__main__':
    main()
