"""
Part of onenv tool that allows to display logs of chosen pod.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import argparse
import sys
import pyperclip
import pods
import helm
import user_config
import console

SCRIPT_DESCRIPTION = 'Displays logs of chosen pod - by default the output of ' \
                     'container entrypoint.'

parser = argparse.ArgumentParser(
    prog='onenv logs',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    description=SCRIPT_DESCRIPTION
)

parser.add_argument(
    type=str,
    nargs='?',
    action='store',
    default=argparse.SUPPRESS,
    help='pod name (or matching pattern, use "-" for wildcard)',
    dest='pod')

parser.add_argument(
    '-f', '--follow',
    action='store_true',
    default=False,
    help='logs will be streamed',
    dest='follow')

parser.add_argument(
    '-i', '--infinity',
    action='store_true',
    default=False,
    help='can be used with -f, the process will keep living waiting for logs '
         'to appear, even between env restarts.',
    dest='infinity')

parser.add_argument(
    '-w', '--worker',
    action='store_true',
    default=argparse.SUPPRESS,
    help='display info level logs from (op|oz)-worker',
    dest='worker')

parser.add_argument(
    '-p', '--panel',
    action='store_true',
    default=argparse.SUPPRESS,
    help='display info level logs from (op|oz)-panel',
    dest='panel')

parser.add_argument(
    '-c', '--cluster-manager',
    action='store_true',
    default=argparse.SUPPRESS,
    help='display info level logs from cluster-manager',
    dest='cluster_manager')

parser.add_argument(
    '-l', '--log-file',
    type=str,
    action='store',
    default='info.log',
    help='log file to be displayed (.log extension can be omitted)',
    dest='logfile')

parser.add_argument(
    '-s', '--show-log-files',
    action='store_true',
    default=False,
    help='show available log files for given app',
    dest='show_logfiles')

parser.add_argument(
    '-x', '--clipboard',
    action='store_true',
    default=False,
    help='copy the output to clipboard',
    dest='clipboard')

user_config.ensure_exists()
args = parser.parse_args()


def logs(pod):
    interactive = not args.clipboard

    if 'worker' in args:
        res = pods.app_logs(pod, app_type='worker', logfile=args.logfile,
                            interactive=interactive,
                            follow=args.follow, infinite=args.infinity)
    elif 'panel' in args:
        res = pods.app_logs(pod, app_type='panel', logfile=args.logfile,
                            interactive=interactive,
                            follow=args.follow, infinite=args.infinity)
    elif 'cluster_manager' in args:
        res = pods.app_logs(pod, app_type='cluster-manager',
                            logfile=args.logfile, interactive=interactive,
                            follow=args.follow, infinite=args.infinity)
    else:
        res = pods.pod_logs(pod, interactive=interactive,
                            follow=args.follow, infinite=args.infinity)

    if args.clipboard and res:
        pyperclip.copy(res)
        console.info('Logs copied to clipboard')


def show_logfiles(pod):
    if 'worker' in args:
        pods.list_logfiles(pod, app_type='worker')
    elif 'panel' in args:
        pods.list_logfiles(pod, app_type='panel')
    elif 'cluster_manager' in args:
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

    if 'pod' not in args:
        args.pod = None

    try:
        if args.show_logfiles:
            pods.match_pod_and_run(args.pod, show_logfiles)
        else:
            pods.match_pod_and_run(args.pod, logs)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()




