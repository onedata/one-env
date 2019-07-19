"""
Part of onenv tool that starts a onedata deployment on kubernetes cluster.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import argparse

from . import onenv_clean
from .utils.deployment import scenario_runner
from .utils import terminal, arg_help_formatter
from .utils.k8s import helm
from .utils.one_env_dir import user_config, deployments_dir, env_config


def delete_old_deployment() -> None:
    if helm.deployment_exists():
        terminal.warning('Removing the existing deployment (forced)')
        onenv_clean.clean_deployment()


def change_release_name(release_name: str) -> None:
    user_config.update('currentHelmDeploymentName', release_name)


def change_release_name_to_default() -> None:
    default_release_name = user_config.get('defaultHelmDeploymentName')
    change_release_name(default_release_name)


def change_namespace(namespace: str) -> None:
    user_config.update('currentNamespace', namespace)


def change_namespace_to_default() -> None:
    default_namespace = user_config.get('defaultNamespace')
    change_namespace(default_namespace)


def main() -> None:
    up_args_parser = argparse.ArgumentParser(
        prog='onenv up',
        formatter_class=arg_help_formatter.ArgumentsHelpFormatter,
        description='Sets up a onedata deployment on kubernetes cluster.'
    )

    up_args_parser.add_argument(
        nargs='?',
        help='path to deployment description YAML file. It allows to '
             'override one-env defaults, as well as specific variables in '
             'chosen scenario. NOTE: values from env_config file are overriden'
             ' by command-line arguments passed to this script.',
        dest='env_config'
    )

    up_args_parser.add_argument(
        '-sc', '--scenario',
        help='predefined scenario to be set up'
    )

    up_args_parser.add_argument(
        '-f', '--force',
        action='store_true',
        help='forces a new deployment - deletes an old one if present'
    )

    up_args_parser.add_argument(
        '-t', '--timeout',
        type=int,
        help='Timeout (in seconds) after which the script terminates with '
             'failure. It is used only when sources or env configuration is '
             'enabled',
        default=600
    )

    up_args_parser.add_argument(
        '--gui-pkg-verification',
        action='store_true',
        help='enables verification of GUI packages'
    )

    deployment_type_group = up_args_parser.add_mutually_exclusive_group()

    deployment_type_group.add_argument(
        '-s', '--sources',
        action='store_true',
        help='force onedata components to be started from '
             'pre-compiled sources on the host'
    )

    deployment_type_group.add_argument(
        '-p', '--packages',
        action='store_true',
        help='force onedata components to be started from '
             'packages pre-installed in dockers'
    )

    images_group = up_args_parser.add_argument_group('images arguments')

    images_group.add_argument(
        '-zi', '--onezone-image',
        help='onezone image to use',
        dest='onezone_image'
    )

    images_group.add_argument(
        '-pi', '--oneprovider-image',
        help='oneprovider image to use',
        dest='oneprovider_image'
    )

    images_group.add_argument(
        '-ci', '--oneclient-image',
        help='oneclient image to use',
        dest='oneclient_image'
    )

    images_group.add_argument(
        '-ri', '--rest-cli-image',
        help='rest client image to use',
        dest='rest_cli_image'
    )

    images_group.add_argument(
        '-li', '--luma-image',
        help='luma image to use',
        dest='luma_image'
    )

    images_group.add_argument(
        '-n', '--no-pull',
        action='store_true',
        help='do not pull images if they are present on the host',
        dest='no_pull'
    )

    charts_group = up_args_parser.add_argument_group('charts arguments')

    charts_group.add_argument(
        '-lcp', '--local-chart-path',
        help='Path to local charts',
        dest='local_chart_path'
    )

    k8s_group = up_args_parser.add_mutually_exclusive_group()

    k8s_group.add_argument(
        '-ns', '--namespace',
        help='namespace in which release will be deployed'
    )

    k8s_group.add_argument(
        '-kc', '--kube-config',
        help='path to kubectl config file',
        dest='kube_config'
    )

    helm_group = up_args_parser.add_argument_group('helm arguments')

    helm_group.add_argument(
        '-rn', '--release-name',
        help='helm release name',
        dest='release_name')

    helm_group.add_argument(
        '-hc', '--helm-config',
        help='path to helm config file',
        dest='helm_config')

    debug_group = up_args_parser.add_argument_group('debug arguments')

    debug_group.add_argument(
        '-de', '--debug',
        action='store_true',
        help='pass debug flag to helm')

    debug_group.add_argument(
        '-dr', '--dry-run',
        action='store_true',
        help='pass dry-run flag to helm',
        dest='dry_run')

    up_args = up_args_parser.parse_args()
    user_config.ensure_exists()

    if up_args.force:
        delete_old_deployment()
    else:
        helm.ensure_deployment(exists=False, fail_with_error=False)

    if up_args.release_name:
        change_release_name(up_args.release_name)
    else:
        change_release_name_to_default()

    if up_args.namespace:
        change_namespace(up_args.namespace)
    else:
        change_namespace_to_default()

    if up_args.kube_config:
        change_namespace('')

    curr_deployment_dir = deployments_dir.new()

    env_config.coalesce(curr_deployment_dir=curr_deployment_dir,
                        env_config_path=up_args.env_config,
                        scenario=up_args.scenario,
                        sources=up_args.sources,
                        packages=up_args.packages,
                        onezone_image=up_args.onezone_image,
                        oneprovider_image=up_args.oneprovider_image,
                        oneclient_image=up_args.oneclient_image,
                        rest_cli_image=up_args.rest_cli_image,
                        luma_image=up_args.luma_image,
                        no_pull=up_args.no_pull,
                        gui_pkg_verification=up_args.gui_pkg_verification)

    scenario_runner.run_scenario(curr_deployment_dir, up_args.local_chart_path,
                                 up_args.debug, up_args.dry_run,
                                 up_args.timeout)


if __name__ == '__main__':
    main()
