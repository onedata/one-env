"""
Part of onenv tool that allows to display logs of chosen pod.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import argparse
import pyperclip

import pods
import helm
import console
import user_config
import argparse_utils
from names_and_paths import *


SCRIPT_DESCRIPTION = 'Displays logs of chosen pod - by default the output of ' \
                     'container entrypoint.'

parser = argparse.ArgumentParser(
    prog='onenv logs',
    formatter_class=argparse_utils.ArgumentsHelpFormatter,
    description=SCRIPT_DESCRIPTION
)

parser.add_argument(
    type=str,
    nargs='?',
    action='store',
    help='pod name (or matching pattern, use "-" for wildcard)',
    dest='pod')


group = parser.add_mutually_exclusive_group()

group.add_argument(
    '-f', '--follow',
    action='store_true',
    help='logs will be streamed')

group.add_argument(
    '-x', '--clipboard',
    action='store_true',
    help='copy the output to clipboard')

parser.add_argument(
    '-i', '--infinity',
    action='store_true',
    help='can be used with -f, the process will keep living waiting for logs '
         'to appear, even between env restarts.')


components_group = parser.add_mutually_exclusive_group()

components_group.add_argument(
    '-w', '--worker',
    action='store_const',
    help='display info level logs from (op|oz)-worker',
    const=APP_TYPE_WORKER,
    dest='app_type')

components_group.add_argument(
    '-p', '--panel',
    action='store_const',
    help='display info level logs from (op|oz)-panel',
    const=APP_TYPE_PANEL,
    dest='app_type')

components_group.add_argument(
    '-c', '--cluster-manager',
    action='store_const',
    help='display info level logs from cluster-manager',
    const=APP_TYPE_CLUSTER_MANAGER,
    dest='app_type')


parser.add_argument(
    '-l', '--log-file',
    type=str,
    action='store',
    default='info.log',
    help='log file to be displayed (.log extension can be omitted)',
    dest='log_file')

parser.add_argument(
    '-s', '--show-log-files',
    action='store_true',
    help='show available log files for given app',
    dest='show_logfiles')


user_config.ensure_exists()
args = parser.parse_args()


def logs(pod):
    interactive = not args.clipboard
    app_type = args.app_type

    if app_type:
        res = pods.app_logs(pod, app_type=app_type, logfile=args.log_file,
                            interactive=interactive,
                            follow=args.follow, infinite=args.infinity)
    else:
        res = pods.pod_logs(pod, interactive=interactive,
                            follow=args.follow, infinite=args.infinity)

    if args.clipboard and res:
        pyperclip.copy(res)
        console.info('Logs copied to clipboard')


def show_logfiles(pod):
    if args.worker:
        pods.list_logfiles(pod, app_type='worker')
    elif args.panel:
        pods.list_logfiles(pod, app_type='panel')
    elif args.cluster_manager:
        pods.list_logfiles(pod, app_type='cluster-manager')
    else:
        console.error(
            'You must specify for which app logfiles should be listed')


def main():
    if args.follow and args.clipboard:
        console.error('-f and -x options cannot be used together')
        return

    if args.infinity and not args.follow:
        console.error('-i can only be used with -f')
        return

    if not args.follow:
        helm.ensure_deployment(exists=True, fail_with_error=True)

    if not args.pod:
        args.pod = None

    try:
        if args.show_logfiles:
            pods.match_pod_and_run(args.pod, show_logfiles)
        else:
            pods.match_pod_and_run(args.pod, logs)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()




