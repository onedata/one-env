"""
Part of onenv tool that allows to attach directly to erlang VM of chosen pod in
onedata one_env_dir.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"


import argparse
import contextlib

from .utils.k8s import pods, helm
from .utils import arg_help_formatter
from .utils.one_env_dir import user_config
from .utils.names_and_paths import (APP_TYPE_CLUSTER_MANAGER, APP_TYPE_WORKER,
                                    APP_TYPE_PANEL)


def attach_to_pod(pod: str, app_type: str) -> None:
    with contextlib.suppress(KeyboardInterrupt):
        pods.match_pod_and_run(pod, lambda pod: pods.attach(pod, app_type))


def main() -> None:
    attach_args_parser = argparse.ArgumentParser(
        prog='onenv attach',
        formatter_class=arg_help_formatter.ArgumentsHelpFormatter,
        description='Attaches directly to erlang VM in chosen pod. '
                    'By default, will attach to worker console, '
                    'unless other choice is specified in argument.'
    )

    attach_args_parser.add_argument(
        help='pod name (or matching pattern, use "-" for wildcard)',
        dest='pod',
        nargs='?',
        default=None
    )

    components_group = attach_args_parser.add_mutually_exclusive_group()

    components_group.add_argument(
        '-p', '--panel',
        action='store_const',
        help='attach to onepanel\'s console in given pod',
        const=APP_TYPE_PANEL,
        dest='app_type'
    )

    components_group.add_argument(
        '-c', '--cluster-manager',
        action='store_const',
        help='attach to cluster-manager\'s console in given pod',
        const=APP_TYPE_CLUSTER_MANAGER,
        dest='app_type'
    )

    components_group.add_argument(
        '-w', '--worker',
        action='store_const',
        help='attach to (op|oz)-worker console in given pod',
        const=APP_TYPE_WORKER,
        dest='app_type'
    )

    attach_args = attach_args_parser.parse_args()
    app_type = attach_args.app_type or APP_TYPE_WORKER

    user_config.ensure_exists()
    helm.ensure_deployment(exists=True, fail_with_error=True)

    attach_to_pod(attach_args.pod, app_type)


if __name__ == '__main__':
    main()
