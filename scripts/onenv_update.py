"""
Part of onenv tool that allows to update sources in given pod.
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import os
import glob
import time
import argparse
import subprocess as sp
from itertools import chain
from threading import Thread
from typing import List, Dict

import kubernetes

from .utils.k8s import pods, helm
from .utils.yaml_utils import load_yaml
from .utils import terminal, arg_help_formatter
from .utils.one_env_dir import deployments_dir, user_config, deployment_data
from .utils.deployment.sources import rsync_sources_for_oc_pod
from .utils.names_and_paths import (APP_OP_PANEL, APP_OZ_PANEL, APP_ONEZONE,
                                    APP_ONEPROVIDER, APP_CLUSTER_MANAGER,
                                    SERVICE_ONECLIENT)

NEW_PODS_TIMEOUT = 60

GUI_DIRS_TO_SYNC = ['_build/default/rel/*/data/gui_static']
BACKEND_DIRS_TO_SYNC = ['_build/default/lib', 'src', 'include']
ALL_DIRS_TO_SYNC = GUI_DIRS_TO_SYNC + BACKEND_DIRS_TO_SYNC


def delete_oc_pod(pod_name: str) -> None:
    sp.Popen(pods.delete_kube_object_cmd('pod', name=pod_name,
                                         delete_all=False))
    with deployment_data.DEPLOYMENT_DATA_LOCK:
        deployment_data.delete_pod_from_sources(pod_name)


def update_sources_for_oc(pod_name: str, pod_cfg: Dict[str, str],
                          delete_pod: bool = True) -> str:
    oc_pod_substring = ''
    for oc_deployment in deployment_data.get().get('oc-deployments').keys():
        if oc_deployment in pod_name:
            oc_pod_substring = oc_deployment

    pod_names = set(pods.get_name(pod) for pod in pods.list_pods())
    if delete_pod:
        delete_oc_pod(pod_name)

    new_pod_name = ''
    start_time = time.time()
    while (not new_pod_name and
           int(time.time() - start_time) <= NEW_PODS_TIMEOUT):
        curr_pod_names = set(pods.get_name(pod) for pod in pods.list_pods())
        if curr_pod_names != pod_names:
            new_names = curr_pod_names - pod_names
            for name in new_names:
                if oc_pod_substring in name:
                    new_pod_name = name
        pod_names = curr_pod_names
        time.sleep(1)

    log_file_path = os.path.join(deployments_dir.get_current_log_dir(),
                                 '{}_rsync.log'.format(new_pod_name))
    rsync_sources_for_oc_pod(new_pod_name, pod_cfg, log_file_path)
    return new_pod_name


def update_sources_for_oz_op(pod_name: str, sources_path: str,
                             dirs_to_sync: List[str],
                             delete: bool = False) -> None:
    for dir_to_sync in dirs_to_sync:
        dir_path = os.path.join(sources_path, dir_to_sync)
        for expanded_path in glob.glob(dir_path):
            destination_path = '{}:{}'.format(pod_name,
                                              os.path.dirname(expanded_path))

            if os.path.exists(expanded_path):
                rsync_cmd = pods.rsync_cmd(expanded_path, destination_path,
                                           delete)
                sp.call(rsync_cmd)


def update_sources_in_pod(pod: kubernetes.client.V1Pod,
                          sources_to_update: List[str],
                          dirs_to_sync: List[str],
                          delete: bool = False) -> None:
    deployment_dir = deployments_dir.get_current_deployment_dir()
    deployment_data_path = os.path.join(deployment_dir, 'deployment_data.yml')
    try:
        deployment_cfg = load_yaml(deployment_data_path)
    except FileNotFoundError:
        terminal.error('File {} containing deployment data not found. '
                       'Is deployment started from sources?'
                       .format(deployment_data_path))
    else:
        pod_name = pods.get_name(pod)
        service_type = pods.get_service_type(pod)
        pod_cfg = deployment_cfg.get('sources').get(pod_name)

        if pod_cfg:
            if service_type == SERVICE_ONECLIENT:
                update_sources_for_oc(pod_name, pod_cfg)
            else:
                for sources_name, sources_path in pod_cfg.items():
                    if sources_name in sources_to_update:
                        update_sources_for_oz_op(pod_name, sources_path,
                                                 dirs_to_sync, delete)


def update_oc_deployment(deployment_substring: str) -> None:
    oc_deployments = deployment_data.get(default={}).get('oc-deployments', {})
    deployment_name = deployment_data.get_oc_deployment_name(deployment_substring,
                                                             oc_deployments)
    deployment_cfg = oc_deployments.get(deployment_name)

    pod_names = set(pods.get_name(pod) for pod in pods.list_pods())
    deployment_pods = [pods.get_name(pod)
                       for pod in pods.list_pods()
                       if deployment_name in pods.get_name(pod)]

    threads = []
    for pod_name in deployment_pods:
        thread = Thread(target=delete_oc_pod, args=(pod_name,))
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join()

    threads = []
    start_time = time.time()
    while (len(threads) < len(deployment_pods) and
           int(time.time() - start_time) <= NEW_PODS_TIMEOUT):
        curr_pod_names = set(pods.get_name(pod) for pod in pods.list_pods())
        new_pods = curr_pod_names - pod_names
        for pod_name in new_pods:
            if deployment_name in pod_name:
                log_dir = deployments_dir.get_current_log_dir()
                log_file_path = os.path.join(log_dir, '{}_rsync.log'
                                             .format(pod_name))
                thread = Thread(target=rsync_sources_for_oc_pod,
                                args=(pod_name, deployment_cfg, log_file_path))
                thread.start()
                threads.append(thread)
        time.sleep(1)
    for thread in threads:
        thread.join()


def update_deployment(sources_to_update: List[str], dirs_to_sync: List[str],
                      delete: bool = False) -> None:
    threads = []
    for pod in pods.list_pods():
        thread = Thread(target=update_sources_in_pod,
                        args=(pod, sources_to_update, dirs_to_sync, delete))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()


def main() -> None:
    update_args_parser = argparse.ArgumentParser(
        prog='onenv update',
        formatter_class=arg_help_formatter.ArgumentsHelpFormatter,
        description='Update sources in given pod or for the whole deployment '
                    'if pod is not specified. By default all sources '
                    'will be updated unless other choice is specified in '
                    'argument.'
    )

    update_args_parser.add_argument(
        nargs='?',
        dest='name',
        help='Pod name (or matching pattern, use "-" for wildcard).'
             'If --oc-deployment flag is present this will match name '
             'of oneclient deployment, and whole oneclient deployment will '
             'be updated. If not specified whole deployment will be updated.'
    )

    update_args_parser.add_argument(
        '-d', '--delete',
        help='specifies if rsync should delete files in pods when they are '
             'deleted on host',
        action='store_true'
    )

    update_args_parser.add_argument(
        '-p', '--panel',
        action='append_const',
        help='update sources for onepanel service',
        dest='sources_to_update',
        const=[APP_OZ_PANEL, APP_OP_PANEL]
    )

    update_args_parser.add_argument(
        '-c', '--cluster-manager',
        action='append_const',
        help='update sources for cluster-manager service',
        dest='sources_to_update',
        const=[APP_CLUSTER_MANAGER]
    )

    update_args_parser.add_argument(
        '-w', '--worker',
        action='append_const',
        help='update sources for (op|oz)-worker',
        dest='sources_to_update',
        const=[APP_ONEZONE, APP_ONEPROVIDER]
    )

    update_args_parser.add_argument(
        '-a', '--all',
        action='store_true',
        help='update sources for all services',
    )

    update_args_parser.add_argument(
        '--oc-deployment',
        action='store_true',
        help='if present name will match whole oneclient deployment instead '
             'of single pod'
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

    if update_args.sources_to_update:
        sources_to_update = list(chain(*update_args.sources_to_update))

    if update_args.all or not sources_to_update:
        sources_to_update = [APP_OZ_PANEL, APP_OP_PANEL, APP_ONEZONE,
                             APP_ONEPROVIDER, APP_CLUSTER_MANAGER]

    dirs_to_sync = update_args.dirs_to_sync or ALL_DIRS_TO_SYNC

    if update_args.name:
        if not update_args.oc_deployment:
            pods.match_pod_and_run(update_args.name, update_sources_in_pod,
                                   sources_to_update, dirs_to_sync,
                                   update_args.delete)
        else:
            update_oc_deployment(update_args.name)
    else:
        update_deployment(sources_to_update, dirs_to_sync, update_args.delete)


if __name__ == '__main__':
    main()
