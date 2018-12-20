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
from itertools import chain

import kubernetes
from watchdog.observers.api import EventQueue
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from .utils import terminal, arg_help_formatter
from .utils.k8s import pods, kubernetes_utils, helm
from .utils.one_env_dir import deployment_data, user_config
from .onenv_update import (update_sources_for_oz_op, GUI_DIRS_TO_SYNC,
                           BACKEND_DIRS_TO_SYNC, ALL_DIRS_TO_SYNC,
                           update_sources_for_oc, update_oc_deployment)
from .utils.names_and_paths import (APP_OP_PANEL, APP_OZ_PANEL, APP_ONEZONE,
                                    APP_ONEPROVIDER, APP_CLUSTER_MANAGER,
                                    SERVICE_ONECLIENT)


BATCH_SIZE = 1000


class BaseHandler(FileSystemEventHandler):
    def __init__(self, name: str, source_path: str, queue: EventQueue,
                 delete: bool = False):
        super().__init__()
        self.name = name
        self.source_path = source_path
        self.event_queue = queue
        self.delete = delete


class OzOpHandler(BaseHandler):
    def __init__(self, name: str, source_path: str,
                 dir_to_sync: str, queue: EventQueue,
                 delete: bool = False):
        super().__init__(name, source_path, queue, delete)
        self.dir_to_sync = dir_to_sync

    def on_any_event(self, event: FileSystemEvent) -> None:
        counter = 0
        while not self.event_queue.empty() and counter < BATCH_SIZE:
            self.event_queue.get()
            counter += 1
        update_sources_for_oz_op(self.name, self.source_path,
                                 [self.dir_to_sync], self.delete)


class OcHandler(BaseHandler):
    def __init__(self, name: str, source_path: str, queue: EventQueue,
                 deployment: bool = False):
        super().__init__(name, source_path, queue)
        self.deployment = deployment

    def on_modified(self, event: FileSystemEvent) -> None:
        counter = 0
        if event.src_path == self.source_path:
            oneclient_changed = True
            time.sleep(1)
        else:
            oneclient_changed = False

        while not self.event_queue.empty() and counter < BATCH_SIZE:
            event = self.event_queue.get()
            if event[0].src_path == self.source_path:
                oneclient_changed = True
            counter += 1

        if oneclient_changed:
            if self.deployment:
                update_oc_deployment(self.name)
            else:
                self.name = update_sources_for_oc(self.name,
                                                  self.source_path)


def run_oz_op_observer(pod_name: str, source_path: str, dir_to_sync: str,
                       delete: bool = False) -> Observer:
    observer = Observer()
    event_handler = OzOpHandler(pod_name, source_path, dir_to_sync,
                                observer.event_queue, delete)

    observer.schedule(event_handler, dir_to_sync, recursive=True)
    observer.start()

    # update sources to have up-to-date version
    update_sources_for_oz_op(pod_name, source_path, [dir_to_sync],
                             delete)

    return observer


def run_oc_observer(name: str, source_path: str,
                    deployment: bool) -> Observer:
    if deployment:
        update_oc_deployment(name)
    else:
        name = update_sources_for_oc(name, source_path)

    observer = Observer()
    event_handler = OcHandler(name, source_path, observer.event_queue,
                              deployment)

    observer.schedule(event_handler, os.path.dirname(source_path))
    observer.start()

    return observer


def run_oc_observers(pod_name: str, source_path: str,
                     deployment: bool = False) -> List[Observer]:
    observers = []
    terminal.info('Starting watcher for {}'.format(source_path))
    observers.append(run_oc_observer(pod_name, source_path, deployment))
    return observers


def run_oz_op_observers(pod_name: str, source_path: str,
                        dirs_to_sync: List[str] = None,
                        delete: bool = False) -> List[Observer]:
    observers = []

    for dir_to_sync in dirs_to_sync:
        dir_to_sync = os.path.join(source_path, dir_to_sync)
        for expanded_path in glob.glob(dir_to_sync):
            terminal.info('Starting watcher for {}'
                          .format(expanded_path))
            observers.append(run_oz_op_observer(pod_name, source_path,
                                                expanded_path, delete))

    return observers


def watch_pod_sources(pod: kubernetes.client.V1Pod,
                      sources_to_update: List[str],
                      dirs_to_sync: List[str],
                      delete: bool = False) -> None:
    curr_deployment_data = deployment_data.get()

    if not curr_deployment_data:
        terminal.error('File {} containing deployment data not found. '
                       'Is deployment started from sources?'
                       .format(deployment_data
                               .get_current_deployment_data_path()))
        return

    pod_name = kubernetes_utils.get_name(pod)
    service_type = pods.get_service_type(pod)
    pod_cfg = curr_deployment_data.get('sources').get(pod_name)
    observers = []

    if pod_cfg:
        for source_name, source_path in pod_cfg.items():
            if service_type == SERVICE_ONECLIENT:
                observers.extend(run_oc_observers(pod_name, source_path))
            elif source_name in sources_to_update:
                observers.extend(run_oz_op_observers(pod_name,
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


def watch_oc_deployment(deployment_substring: str) -> None:
    oc_deployments = deployment_data.get(default={}).get('oc-deployments', {})
    deployment_name = deployment_data.get_oc_deployment_name(deployment_substring,
                                                             oc_deployments)
    source_path = oc_deployments.get(deployment_name).get(SERVICE_ONECLIENT)
    observers = run_oc_observers(deployment_name, source_path,
                                 deployment=True)
    try:
        while True:
            time.sleep(2)
    except KeyboardInterrupt:
        for observer in observers:
            observer.stop()
            observer.join()


def main() -> None:
    watch_args_parser = argparse.ArgumentParser(
        prog='onenv watch',
        formatter_class=arg_help_formatter.ArgumentsHelpFormatter,
        description='Watch for sources change and automatically updates '
                    'sources in given pod or the whole deployment if pod is '
                    'not specified. By default all sources will be watched '
                    'unless other choice is specified in argument.'
    )

    watch_args_parser.add_argument(
        help='Pod name (or matching pattern, use "-" for wildcard).'
             'If --oc-deployment flag is present this will match name '
             'of oneclient deployment, and whole oneclient deployment will '
             'be updated. If not specified whole deployment will be updated.',
        nargs='?',
        dest='name'
    )

    watch_args_parser.add_argument(
        '-d', '--delete',
        action='store_true',
        help='specifies if rsync should delete files in pods when they are '
             'deleted on host'
    )

    watch_args_parser.add_argument(
        '-p', '--panel',
        action='append_const',
        help='watch sources for onepanel service',
        dest='sources_to_update',
        const=[APP_OZ_PANEL, APP_OP_PANEL]
    )

    watch_args_parser.add_argument(
        '-c', '--cluster-manager',
        action='append_const',
        help='watch sources for cluster-manager service',
        dest='sources_to_update',
        const=[APP_CLUSTER_MANAGER]
    )

    watch_args_parser.add_argument(
        '-w', '--worker',
        action='append_const',
        help='watch sources for (op|oz)-worker',
        dest='sources_to_update',
        const=[APP_ONEZONE, APP_ONEPROVIDER]
    )

    watch_args_parser.add_argument(
        '-a', '--all',
        action='store_true',
        help='watch sources for all services',
    )

    watch_args_parser.add_argument(
        '--oc-deployment',
        action='store_true',
        help='if present name will match whole oneclient deployment instead '
             'of single pod. For each pod watcher will be started.'
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

    if watch_args.sources_to_update:
        sources_to_update = list(chain(*watch_args.sources_to_update))

    if watch_args.all or not sources_to_update:
        sources_to_update = [APP_OZ_PANEL, APP_OP_PANEL, APP_ONEZONE,
                             APP_ONEPROVIDER, APP_CLUSTER_MANAGER]

    dirs_to_sync = watch_args.dirs_to_sync or ALL_DIRS_TO_SYNC

    if watch_args.name:
        if not watch_args.oc_deployment:
            pods.match_pod_and_run(watch_args.name, watch_pod_sources,
                                   sources_to_update, dirs_to_sync,
                                   watch_args.delete)
        else:
            watch_oc_deployment(watch_args.name)
    else:
        watch_deployment_sources(sources_to_update, dirs_to_sync,
                                 watch_args.delete)


if __name__ == '__main__':
    main()
