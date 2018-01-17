"""
Part of onenv tool that starts a onedata deployment on kubernetes cluster.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import sys
import argparse
import console
import binaries
import user_config
import env_config
import deployments_dir
import scenario_runner

SCRIPT_DESCRIPTION = 'Sets up a onedata deployment on kubernetes cluster.'

parser = argparse.ArgumentParser(
    prog='onenv up',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    description=SCRIPT_DESCRIPTION
)

parser.add_argument(
    '-e', '--env-desc',
    type=str,
    action='store',
    default=None,
    help='Path to environment description YAML file. It allows to override '
         'one-env defaults, as well as specific variables in chosen scenario. '
         'NOTE: values from env_config file are overriden by command-line '
         'arguments passed to this script.',
    dest='env_config')

parser.add_argument(
    '-s', '--scenario',
    type=str,
    action='store',
    default='scenario-1oz-1op',
    help='predefined scenario to be set up',
    dest='scenario')

parser.add_argument(
    '-b', '--binaries',
    action='store_true',
    default=None,
    help='Forces onedata components to be started from '
         'precompiled binaries on the host',
    dest='binaries')

parser.add_argument(
    '-p', '--packages',
    action='store_true',
    default=None,
    help='Forces onedata components to be started from '
         'packages pre-installed in dockers',
    dest='packages')

parser.add_argument(
    '-zi', '--onezone-image',
    type=str,
    action='store',
    default=None,
    help='Onezone image to use',
    dest='onezone_image')

parser.add_argument(
    '-pi', '--oneprovider-image',
    type=str,
    action='store',
    default=None,
    help='Oneprovider image to use',
    dest='oneprovider_image')

parser.add_argument(
    '-n', '--no-pull',
    action='store_true',
    default=None,
    help='Do not pull images if they are present on the host',
    dest='no_pull')

args = parser.parse_args()

if args.binaries and args.packages:
    console.error('-b and -p options cannot be used together')
    sys.exit(1)

if not user_config.exists():
    user_config.initialize()

env_config_output_dir = deployments_dir.new()

env_config.coalesce(env_config_output_dir, args.env_config, args.scenario,
                    args.binaries, args.packages, args.onezone_image,
                    args.oneprovider_image, args.no_pull)

scenario_runner.run_scenario(env_config_output_dir)

# TODO w tym katalogu jest przygotowany env_config.yaml, odpalasz tutaj swoj
# TODO skrypt
print('o tutej: ' + env_config_output_dir)

# print(user_config.get('hostHomeDir'))
# print(user_config.get('kubeHostHomeDir'))
# print(binaries.locate('op-worker'))
