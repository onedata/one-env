"""
Part of onenv tool that allows to exec to chosen pod in onedata deployment.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import argparse
import pods
import console

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
    default=None,
    help='Pod name (or any matching, unambiguous substring)',
    dest='pod')

args = parser.parse_args()

pods.match_pod_and_run(args.pod, pods.exec)
