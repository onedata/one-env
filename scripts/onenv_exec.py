"""
Part of onenv tool that allows to exec to chosen pod in onedata deployment.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import argparse
import pods
import helm
import user_config

SCRIPT_DESCRIPTION = 'Execs to chosen pod with an interactive shell.'

parser = argparse.ArgumentParser(
    prog='onenv exec',
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

user_config.ensure_exists()
helm.ensure_deployment(exists=True, fail_with_error=True)

args = parser.parse_args()
if 'pod' not in args:
    args.pod = None

try:
    pods.match_pod_and_run(args.pod, pods.pod_exec)
except KeyboardInterrupt:
    pass
