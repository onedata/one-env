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
import helm
import user_config
import env_config
import deployments_dir
import scenario_runner
import pods


SCRIPT_DESCRIPTION = 'Sets up a onedata deployment on kubernetes cluster.'

parser = argparse.ArgumentParser(
    prog='onenv up',
    description=SCRIPT_DESCRIPTION
)


#TODO: FIX DEFAULTS LATER
parser.add_argument(
    type=str,
    nargs='?',
    action='store',
    help='path to environment description YAML file. It allows to override '
         'one-env defaults, as well as specific variables in chosen scenario. '
         'NOTE: values from env_config file are overriden by command-line '
         'arguments passed to this script.',
    dest='env_config')

parser.add_argument(
    '-sc', '--scenario',
    type=str,
    action='store',
    help='predefined scenario to be set up',
    dest='scenario')

parser.add_argument(
    '-f', '--force',
    action='store_true',
    help='forces a new deployment - deletes an old one if present',
    dest='force')


components_group = parser.add_mutually_exclusive_group()

components_group.add_argument(
    '-s', '--sources',
    action='store_true',
    help='force onedata components to be started from '
         'pre-compiled sources on the host',
    dest='sources')

components_group.add_argument(
    '-p', '--packages',
    action='store_true',
    help='force onedata components to be started from '
         'packages pre-installed in dockers',
    dest='packages')


images_group = parser.add_argument_group('images arguments')

images_group.add_argument(
    '-zi', '--onezone-image',
    type=str,
    action='store',
    help='onezone image to use',
    dest='onezone_image')

images_group.add_argument(
    '-pi', '--oneprovider-image',
    type=str,
    action='store',
    help='oneprovider image to use',
    dest='oneprovider_image')

images_group.add_argument(
    '-ci', '--oneclient-image',
    type=str,
    action='store',
    help='oneclient image to use',
    dest='oneclient_image')

images_group.add_argument(
    '-ri', '--rest-cli-image',
    type=str,
    action='store',
    help='rest client image to use',
    dest='rest_cli_image')

images_group.add_argument(
    '-li', '--luma-image',
    type=str,
    action='store',
    help='luma image to use',
    dest='luma_image')

images_group.add_argument(
    '-n', '--no-pull',
    action='store_true',
    help='do not pull images if they are present on the host',
    dest='no_pull')


charts_group = parser.add_argument_group('charts arguments')

charts_group.add_argument(
    '-l', '--local',
    action='store_true',
    help='If present local charts will be used',
    dest='local')

charts_group.add_argument(
    '-cp', '--chart-path',
    action='store',
    default='charts/stable',
    help='Path to local charts (default: %(default)s)',
    dest='chart_path')


k8s_group = parser.add_mutually_exclusive_group()

k8s_group.add_argument(
    '-ns', '--namespace',
    action='store',
    help='namespace in which release will be deployed',
    dest='namespace')

k8s_group.add_argument(
    '-kc', '--kube-config',
    action='store',
    help='path to kubectl config file',
    dest='kube_config')


helm_group = parser.add_argument_group('helm arguments')

helm_group.add_argument(
    '-rn', '--release-name',
    action='store',
    help='helm release name',
    dest='release_name')

helm_group.add_argument(
    '-hc', '--helm-config',
    action='store',
    help='path to helm config file',
    dest='helm_config')


debug_group = parser.add_argument_group('debug arguments')

debug_group.add_argument(
    '-de', '--debug',
    action='store_true',
    help='pass debug flag to helm',
    dest='debug')

debug_group.add_argument(
    '-dr', '--dry-run',
    action='store_true',
    help='pass dry-run flag to helm',
    dest='dry_run')


def delete_old_deployment():
    if helm.deployment_exists():
        console.warning('Removing the existing deployment (forced)')
        helm.clean_deployment()
        pods.clean_jobs()
        pods.clean_pods()


def change_release_name(release_name):
    user_config.update('currentHelmDeploymentName', release_name)


def change_release_name_to_default():
    default_release_name = user_config.get('defaultHelmDeploymentName')
    user_config.update('currentHelmDeploymentName', default_release_name)


def change_namespace(namespace):
    user_config.update('currentNamespace', namespace)


def change_namespace_to_default():
    default_namespace = user_config.get('defaultNamespace')
    user_config.update('currentNamespace', default_namespace)


def main():
    args = parser.parse_args()
    user_config.ensure_exists()

    if args.force:
        delete_old_deployment()
    else:
        helm.ensure_deployment(exists=False, fail_with_error=True)

    if args.release_name:
        change_release_name(args.release_name)
    else:
        change_release_name_to_default()

    if args.namespace:
        change_namespace(args.namespace)
    else:
        change_namespace_to_default()

    if args.kube_config:
        change_namespace('')

    env_config_output_dir = deployments_dir.new()

    env_config.coalesce(env_config_output_dir, args.env_config,
                        args.scenario, args.sources, args.packages,
                        args.onezone_image, args.oneprovider_image,
                        args.no_pull)

    scenario_runner.run_scenario(env_config_output_dir, args.local,
                                 args.debug, args.dry_run)


if __name__ == '__main__':
    main()
