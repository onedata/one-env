"""
Part of onenv tool that allows to automatically update sources in current
deployment.
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"


import os
import yaml
import time
import threading
import argparse
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import console
import deployments_dir
from argparse_utils import ArgumentsHelpFormatter
from onenv_update import update_sources_in_pod
import pods
import kubernetes_utils


SCRIPT_DESCRIPTION = 'Watch for sources change for given directory'

parser = argparse.ArgumentParser(
    prog='onenv watch',
    formatter_class=ArgumentsHelpFormatter,
    description=SCRIPT_DESCRIPTION
)

parser.add_argument(
    type=str,
    nargs='?',
    action='store',
    help='pod name (or matching pattern, use "-" for wildcard) - '
         'display detailed status of given pod.',
    dest='pod')


args = parser.parse_args()


class Handler(FileSystemEventHandler):
    def __init__(self, pod_name, source_path):
        super().__init__()
        self.pod_name = pod_name
        self.source_path = source_path

    def on_any_event(self, event):
        update_sources_in_pod(self.pod_name)


def run(pod_name, path):
    observer = Observer()
    event_handler = Handler(pod_name, path)

    observer.schedule(event_handler, path, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(2)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()


def watch_pod_sources(pod):
    deployment_dir = deployments_dir.current_deployment_dir()

    try:
        with open(os.path.join(deployment_dir, 'deployment_data.yml')) as \
                deployment_data_file:
            deployment_data = yaml.load(deployment_data_file)

            pod_name = kubernetes_utils.get_name(pod)
            pod_cfg = deployment_data.get('sources').get(pod_name).items()

            for source, source_path in pod_cfg:
                console.info('Starting watcher for directory {}'.format(
                    source_path))
                t = threading.Thread(target=run, args=(pod_name, source_path))
                t.start()
    except FileNotFoundError:
        console.error('File {} containing deployment data not found. '
                      'Is service started from sources?')


def watch_deployment_sources():
    pods_list = pods.list_pods()
    for pod in pods_list:
        watch_pod_sources(pod)


if __name__ == '__main__':
    if args.pod:
        pod = pods.match_pods(args.pod)[0]
        watch_pod_sources(pod)
    else:
        watch_deployment_sources()
