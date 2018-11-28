"""
Part of onenv tool that allows to automatically update sources in current
deployment.
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import os
import glob
import time
import argparse
from typing import List

import kubernetes
from watchdog.observers.api import EventQueue
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from .utils import terminal, arg_help_formatter
from .utils.k8s import pods, kubernetes_utils, helm
from .utils.one_env_dir import deployment_data, user_config
from .onenv_update import (update_sources_for_component, GUI_DIRS_TO_SYNC,
                           BACKEND_DIRS_TO_SYNC, ALL_DIRS_TO_SYNC)
from .utils.names_and_paths import (APP_OP_PANEL, APP_OZ_PANEL, APP_ONEZONE,
                                    APP_ONEPROVIDER, APP_CLUSTER_MANAGER)


BATCH_SIZE = 1000


class Handler(FileSystemEventHandler):
    def __init__(self, pod_name: str, source_path: str,
                 dir_to_sync: str, queue: EventQueue,
                 delete: bool = False):
        super().__init__()
        self.pod_name = pod_name
        self.source_path = source_path
        self.dir_to_sync = dir_to_sync
        self.event_queue = queue
        self.delete = delete

    def on_any_event(self, event: FileSystemEvent) -> None:
        counter = 0
        while not self.event_queue.empty() and counter < BATCH_SIZE:
            self.event_queue.get()
            counter += 1
        update_sources_for_component(self.pod_name, self.source_path,
                                     [self.dir_to_sync], self.delete)


def run(pod_name: str, source_path: str, dir_to_sync: str,
        delete: bool = False) -> Observer:
    observer = Observer()
    event_handler = Handler(pod_name, source_path, dir_to_sync,
                            observer.event_queue, delete)

    observer.schedule(event_handler, dir_to_sync, recursive=True)
    observer.start()

    # update sources to have up-to-date version
    update_sources_for_component(pod_name, source_path, [dir_to_sync], delete)

    return observer


def create_observers_for_source(pod_name: str, source_path: str,
                                dirs_to_sync: List[str], delete: bool = False):
    observers = []
    for dir_to_sync in dirs_to_sync:
        dir_to_sync = os.path.join(source_path, dir_to_sync)
        for expanded_path in glob.glob(dir_to_sync):
            terminal.info('Starting watcher for directory {}'
                          .format(expanded_path))
            observers.append(run(pod_name, source_path, expanded_path, delete))
    return observers


def watch_pod_sources(pod: kubernetes.client.V1Pod,
                      sources_to_update: List[str],
                      dirs_to_sync: List[str],
                      delete: bool = False) -> None:
    curr_deployment_data = deployment_data.get()

    if not curr_deployment_data:
        terminal.error('File {} containing deployment data not found. '
                       'Is service started from sources?'
                       .format(deployment_data
                               .get_current_deployment_data_path()))
        return

    pod_name = kubernetes_utils.get_name(pod)
    pod_cfg = curr_deployment_data.get('sources').get(pod_name)
    observers = []

    if pod_cfg:
        for source_name, source_path in pod_cfg.items():
            if source_name in sources_to_update:
                observers.extend(create_observers_for_source(pod_name,
                                                             source_path,
                                                             dirs_to_sync,
                                                             delete))

    try:
        while True:
            time.sleep(2)
    except KeyboardInterrupt:
        for observer in observers:
            observer.stop()
            observer.join()


def watch_deployment_sources(sources_to_update: List[str],
                             dirs_to_sync: List[str],
                             delete: bool = False) -> None:
    for pod in pods.list_pods():
        watch_pod_sources(pod, sources_to_update, dirs_to_sync, delete)


def main() -> None:
    watch_args_parser = argparse.ArgumentParser(
        prog='onenv watch',
        formatter_class=arg_help_formatter.ArgumentsHelpFormatter,
        description='Watch for sources change for given directory'
    )

    watch_args_parser.add_argument(
        help='pod name (or matching pattern, use "-" for wildcard) - '
             'display detailed status of given pod.',
        nargs='?',
        dest='pod'
    )

    watch_args_parser.add_argument(
        '-d', '--delete',
        action='store_true',
        help='specifies if rsync should delete files in pods when they are '
             'deleted on host'
    )

    watch_args_parser.add_argument(
        '-p', '--panel',
        action='store_true',
        help='watch sources for onepanel service',
    )

    watch_args_parser.add_argument(
        '-c', '--cluster-manager',
        action='store_true',
        help='watch sources for cluster-manager service',
    )

    watch_args_parser.add_argument(
        '-w', '--worker',
        action='store_true',
        help='watch sources for (op|oz)-worker',
    )

    watch_args_parser.add_argument(
        '-a', '--all',
        action='store_true',
        help='watch sources for all services',
    )

    sources_type = watch_args_parser.add_mutually_exclusive_group()

    sources_type.add_argument(
        '-g', '--gui',
        action='store_const',
        help='watch sources only for GUI',
        dest='dirs_to_sync',
        const=GUI_DIRS_TO_SYNC
    )

    sources_type.add_argument(
        '-b', '--backend',
        action='store_const',
        help='watch sources only for backend',
        dest='dirs_to_sync',
        const=BACKEND_DIRS_TO_SYNC
    )

    watch_args = watch_args_parser.parse_args()

    user_config.ensure_exists()
    helm.ensure_deployment(exists=True, fail_with_error=True)

    sources_to_update = []

    if watch_args.panel:
        sources_to_update.extend([APP_OZ_PANEL, APP_OP_PANEL])
    if watch_args.worker:
        sources_to_update.extend([APP_ONEZONE, APP_ONEPROVIDER])
    if watch_args.cluster_manager:
        sources_to_update.extend([APP_CLUSTER_MANAGER])
    if watch_args.all:
        sources_to_update = [APP_OZ_PANEL, APP_OP_PANEL, APP_ONEZONE,
                             APP_ONEPROVIDER, APP_CLUSTER_MANAGER]

    dirs_to_sync = watch_args.dirs_to_sync or ALL_DIRS_TO_SYNC

    if watch_args.pod:
        pod = pods.match_pods(watch_args.pod)[0]
        watch_pod_sources(pod, sources_to_update, dirs_to_sync,
                          watch_args.delete)
    else:
        watch_deployment_sources(sources_to_update, dirs_to_sync,
                                 watch_args.delete)


if __name__ == '__main__':
    main()
