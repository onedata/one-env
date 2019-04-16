"""
Part of onenv tool that allows to display logs of chosen pod.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import argparse
import contextlib

import pyperclip
from kubernetes.client import V1Pod

from .utils.one_env_dir import user_config
from .utils.k8s import helm, pods
from .utils import terminal, arg_help_formatter
from .utils.names_and_paths import (APP_TYPE_CLUSTER_MANAGER, APP_TYPE_WORKER,
                                    APP_TYPE_PANEL)


def logs(pod: V1Pod, clipboard: bool, app_type: str, log_file: str,
         follow: bool, infinity: bool) -> None:
    interactive = not clipboard
    service_type = pods.get_service_type(pod)

    if app_type:
        res = pods.app_logs(pod, app_type=app_type, logfile=log_file,
                            interactive=interactive,
                            follow=follow, infinite=infinity)
    else:
        res = pods.pod_logs(pod, interactive=interactive,
                            follow=follow, infinite=infinity,
                            container=service_type)

    if clipboard and res:
        pyperclip.copy(res)
        terminal.info('Logs copied to clipboard')


def show_logfiles(pod: V1Pod, app_type: str = 'cluster-manager') -> None:
    if app_type:
        pods.list_logfiles(pod, app_type=app_type)
    else:
        terminal.error('You must specify for which app logfiles '
                       'should be listed')


def main() -> None:
    logs_args_parser = argparse.ArgumentParser(
        prog='onenv logs',
        formatter_class=arg_help_formatter.ArgumentsHelpFormatter,
        description='Displays logs of chosen pod - by default the output '
                    'of container entrypoint.'
    )

    logs_args_parser.add_argument(
        nargs='?',
        help='pod name (or matching pattern, use "-" for wildcard)',
        dest='pod'
    )

    group = logs_args_parser.add_mutually_exclusive_group()

    group.add_argument(
        '-f', '--follow',
        action='store_true',
        help='logs will be streamed'
    )

    group.add_argument(
        '-x', '--clipboard',
        action='store_true',
        help='copy the output to clipboard'
    )

    logs_args_parser.add_argument(
        '-i', '--infinity',
        action='store_true',
        help='can be used with -f, the process will keep living waiting '
             'for logs to appear, even between env restarts.'
    )

    components_group = logs_args_parser.add_mutually_exclusive_group()

    components_group.add_argument(
        '-w', '--worker',
        action='store_const',
        help='display info level logs from (op|oz)-worker',
        const=APP_TYPE_WORKER,
        dest='app_type'
    )

    components_group.add_argument(
        '-c', '--cluster-manager',
        action='store_const',
        help='display info level logs from cluster-manager',
        const=APP_TYPE_CLUSTER_MANAGER,
        dest='app_type'
    )

    components_group.add_argument(
        '-p', '--panel',
        action='store_const',
        help='display info level logs from (op|oz)-panel',
        const=APP_TYPE_PANEL,
        dest='app_type'
    )

    logs_args_parser.add_argument(
        '-l', '--log-file',
        default='info.log',
        help='log file to be displayed (.log extension can be omitted)',
        dest='log_file'
    )

    logs_args_parser.add_argument(
        '-s', '--show-log-files',
        action='store_true',
        help='show available log files for given app',
        dest='show_logfiles'
    )

    logs_args = logs_args_parser.parse_args()

    user_config.ensure_exists()

    if logs_args.infinity and not logs_args.follow:
        terminal.error('-i can only be used with -f')
        return

    if not logs_args.follow:
        helm.ensure_deployment(exists=True, fail_with_error=True)

    with contextlib.suppress(KeyboardInterrupt):
        if logs_args.show_logfiles:
            pods.match_pod_and_run(logs_args.pod, show_logfiles,
                                   logs_args.app_type)
        else:
            pods.match_pod_and_run(logs_args.pod, logs, logs_args.clipboard,
                                   logs_args.app_type, logs_args.log_file,
                                   logs_args.follow, logs_args.infinity)


if __name__ == '__main__':
    main()
