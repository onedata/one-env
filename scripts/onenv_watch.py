"""
Part of onenv tool that allows to automatically update sources in current
deployment.
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import time
import argparse

import kubernetes
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from .utils import terminal, arg_help_formatter
from .utils.k8s import pods, kubernetes_utils, helm
from .utils.one_env_dir import deployment_data, user_config
from .onenv_update import update_sources_for_component, update_sources_in_pod


BATCH_SIZE = 1000


class Handler(FileSystemEventHandler):
    def __init__(self, pod: kubernetes.client.V1Pod, pod_name: str,
                 source_path: str, queue):
        super().__init__()
        self.pod = pod
        self.pod_name = pod_name
        self.source_path = source_path
        self.event_queue = queue

    def on_any_event(self, event: FileSystemEvent) -> None:
        counter = 0
        while not self.event_queue.empty() and counter < BATCH_SIZE:
            self.event_queue.get()
            counter += 1
        update_sources_for_component(self.pod_name, self.source_path)


def run(pod: kubernetes.client.V1Pod, pod_name: str, path: str) -> Observer:
    observer = Observer()
    event_handler = Handler(pod, pod_name, path, observer.event_queue)

    observer.schedule(event_handler, path, recursive=True)
    observer.start()

    # update sources to have up-to-date version
    update_sources_in_pod(pod)

    return observer


def watch_pod_sources(pod: kubernetes.client.V1Pod) -> None:
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
        for source_path in pod_cfg.values():
            terminal.info('Starting watcher for directory {}'
                          .format(source_path))
            observers.append(run(pod, pod_name, source_path))

    try:
        while True:
            time.sleep(2)
    except KeyboardInterrupt:
        for observer in observers:
            observer.stop()
            observer.join()


def watch_deployment_sources() -> None:
    for pod in pods.list_pods():
        watch_pod_sources(pod)


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

    watch_args = watch_args_parser.parse_args()

    user_config.ensure_exists()
    helm.ensure_deployment(exists=True, fail_with_error=True)

    if watch_args.pod:
        pod = pods.match_pods(watch_args.pod)[0]
        watch_pod_sources(pod)
    else:
        watch_deployment_sources()


if __name__ == '__main__':
    main()
