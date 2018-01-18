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
    '-e', '--env-config',
    type=str,
    action='store',
    default=argparse.SUPPRESS,
    help='path to environment description YAML file. It allows to override '
         'one-env defaults, as well as specific variables in chosen scenario. '
         'NOTE: values from env_config file are overriden by command-line '
         'arguments passed to this script.',
    dest='env_config')

parser.add_argument(
    '-s', '--scenario',
    type=str,
    action='store',
    default=argparse.SUPPRESS,
    help='predefined scenario to be set up',
    dest='scenario')

parser.add_argument(
    '-b', '--binaries',
    action='store_true',
    default=argparse.SUPPRESS,
    help='force onedata components to be started from '
         'pre-compiled binaries on the host',
    dest='binaries')

parser.add_argument(
    '-p', '--packages',
    action='store_true',
    default=argparse.SUPPRESS,
    help='force onedata components to be started from '
         'packages pre-installed in dockers',
    dest='packages')

parser.add_argument(
    '-zi', '--onezone-image',
    type=str,
    action='store',
    default=argparse.SUPPRESS,
    help='onezone image to use',
    dest='onezone_image')

parser.add_argument(
    '-pi', '--oneprovider-image',
    type=str,
    action='store',
    default=argparse.SUPPRESS,
    help='oneprovider image to use',
    dest='oneprovider_image')

parser.add_argument(
    '-n', '--no-pull',
    action='store_true',
    default=argparse.SUPPRESS,
    help='do not pull images if they are present on the host',
    dest='no_pull')

args = parser.parse_args()
if 'env_config' not in args:
    args.env_config = None
if 'scenario' not in args:
    args.scenario = None
if 'binaries' not in args:
    args.binaries = None
if 'packages' not in args:
    args.packages = None
if 'onezone_image' not in args:
    args.onezone_image = None
if 'oneprovider_image' not in args:
    args.oneprovider_image = None
if 'no_pull' not in args:
    args.no_pull = None

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
