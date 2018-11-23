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

import kubernetes

from .utils.k8s import pods, helm
from .utils.yaml_utils import load_yaml
from .utils import terminal, arg_help_formatter
from .utils.one_env_dir import deployments_dir, user_config


DIRS_TO_SYNC = ['_build/default/rel/*/data/gui_static', '_build/default/lib',
                'src', 'include']


def update_sources_for_component(pod_name: str, source_path: str) -> None:
    for dir_to_sync in DIRS_TO_SYNC:
        dir_path = os.path.join(source_path, dir_to_sync)
        for expanded_path in glob.glob(dir_path):
            destination_path = '{}:{}'.format(pod_name,
                                              os.path.dirname(expanded_path))

            if os.path.exists(expanded_path):
                subprocess.call(pods.rsync_cmd(expanded_path,
                                               destination_path), shell=True)


def update_sources_in_pod(pod: kubernetes.client.V1Pod) -> None:
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
            for source_path in pod_cfg.values():
                update_sources_for_component(pod_name, source_path)


def update_deployment() -> None:
    for pod in pods.list_pods():
        update_sources_in_pod(pod)


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

    update_args = update_args_parser.parse_args()

    user_config.ensure_exists()
    helm.ensure_deployment(exists=True, fail_with_error=True)

    if update_args.pod:
        pods.match_pod_and_run(update_args.pod, update_sources_in_pod)
    else:
        update_deployment()


if __name__ == '__main__':
    main()
