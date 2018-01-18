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

SCRIPT_DESCRIPTION = 'Displays logs of chosen pod.'

parser = argparse.ArgumentParser(
    prog='onenv logs',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    description=SCRIPT_DESCRIPTION
)

parser.add_argument(
    '-f', '--follow',
    action='store_true',
    default=False,
    help='logs will be streamed',
    dest='follow')

parser.add_argument(
    type=str,
    nargs='?',
    action='store',
    default=argparse.SUPPRESS,
    help='pod name (or any matching, unambiguous substring)',
    dest='pod')

user_config.ensure_exists()
helm.ensure_deployment(exists=True, fail_with_error=True)

args = parser.parse_args()
if 'pod' not in args:
    args.pod = None


def logs(pod):
    pods.logs(pod, interactive=True, follow=args.follow)


try:
    pods.match_pod_and_run(args.pod, logs)
except KeyboardInterrupt:
    pass
