"""
Part of onenv tool that allows to display logs of chosen pod.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import argparse
import pods
import helm
import user_config

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
    help='pod name (or any matching, unambiguous substring)',
    dest='pod')

parser.add_argument(
    '-f', '--follow',
    action='store_true',
    default=False,
    help='logs will be streamed',
    dest='follow')

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

user_config.ensure_exists()
helm.ensure_deployment(exists=True, fail_with_error=True)

args = parser.parse_args()
if 'pod' not in args:
    args.pod = None


def logs(pod):
    if 'worker' in args:
        pods.app_logs(pod, 'worker', interactive=True, follow=args.follow)
    elif 'panel' in args:
        pods.app_logs(pod, 'panel', interactive=True, follow=args.follow)
    elif 'cluster_manager' in args:
        pods.app_logs(pod, 'cluster-manager', interactive=True,
                      follow=args.follow)
    else:
        pods.logs(pod, interactive=True, follow=args.follow)


try:
    pods.match_pod_and_run(args.pod, logs)
except KeyboardInterrupt:
    pass
