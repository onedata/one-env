"""
Main script for setting up a onedata deployment on kubernetes cluster.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import argparse
import user_config
import binaries

SCRIPT_DESCRIPTION = 'Sets up a onedata deployment on kubernetes cluster.'

parser = argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    description=SCRIPT_DESCRIPTION
)

parser.add_argument(
    '-s', '--scenario',
    type=str,
    action='store',
    default='1op_1oz',
    help='predefined scenario to be set up',
    dest='scenario')

parser.add_argument(
    '-b', '--binaries',
    action='store_true',
    default=False,
    help='Toggles if onedata components should be started from precompiled '
         'binaries on the host or packages pre-installed in dockers',
    dest='binaries')

args = parser.parse_args()

if not user_config.exists():
    user_config.initialize()

print(user_config.get('hostHomeDir'))
print(user_config.get('kubeHostHomeDir'))
print(binaries.locate('op-worker'))

