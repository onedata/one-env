"""
Part of onenv tool that allows to start oneclient service in pod.
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import os
import re
import sys
import argparse
import contextlib
from typing import Dict, Any, Optional

from .utils import shell
from .utils.k8s import pods, helm
from .utils.deployment import sources
from .utils import arg_help_formatter
from .utils.one_env_dir import user_config
from .utils.one_env_dir import deployment_data
from .utils.one_env_dir import deployments_dir
from .utils.deployment.sources_paths import locate_oc
from .utils.yaml_utils import load_yaml, dump_yaml
from .utils.deployment.config_parser import set_release_name_override
from .utils.names_and_paths import SERVICE_ONECLIENT, ONECLIENT_CHART_REPO_PATH


def get_default_cfg() -> Dict[str, Any]:
    script_dir = os.path.dirname(os.path.realpath(__file__))
    default_cfg_path = os.path.join(script_dir, 'utils', 'one_env_dir',
                                    'client_values.yaml')
    return load_yaml(default_cfg_path)


def save_cfg(name: str, cfg: Dict[str, Any]) -> str:
    deployment_dir_path = deployments_dir.get_current_deployment_dir()
    deployment_oneclient_dir_path = os.path.join(deployment_dir_path,
                                                 name)
    values_path = os.path.join(deployment_oneclient_dir_path,
                               'client_values.yaml')
    with contextlib.suppress(OSError):
        os.makedirs(deployment_oneclient_dir_path)
    dump_yaml(cfg, values_path)
    return values_path


def get_provider_suffix(provider_substring: str) -> str:
    chart_name = pods.match_pod_and_run(provider_substring,
                                        pods.get_chart_name)
    if chart_name is None:
        sys.exit(1)
    suffix = re.search('oneprovider-(.*)', chart_name, re.IGNORECASE)[1]
    return suffix


def start_oneclient_deployment(*, name: str, release_name: str,
                               deployment_release_name: str,
                               oneclient_cfg_path: Optional[str] = None,
                               direct_io: bool = False,
                               provider_substring: Optional[str] = None,
                               image: Optional[str] = None) -> str:
    helm.add_onedata_repo()
    pod_substring = '{}-{}'.format(deployment_release_name, name)

    if oneclient_cfg_path:
        oneclient_cfg = {**get_default_cfg(), **load_yaml(oneclient_cfg_path)}
    else:
        oneclient_cfg = get_default_cfg()

    set_release_name_override(oneclient_cfg, deployment_release_name)
    oneclient_cfg['nameOverride'] = name

    if provider_substring:
        provider_suffix = get_provider_suffix(provider_substring)
        oneclient_cfg['suffix'] = provider_suffix
        pod_substring += '-{}'.format(provider_suffix)

    if image:
        oneclient_cfg['image'] = image

    if direct_io:
        oneclient_cfg['directIO']['nfs']['enabled'] = True

    deployment_cfg_path = save_cfg(name, oneclient_cfg)
    helm_install_cmd = helm.install_cmd(ONECLIENT_CHART_REPO_PATH,
                                        [deployment_cfg_path],
                                        release_name=release_name)
    shell.call(helm_install_cmd)
    deployment_data.add_release(release_name)
    return pod_substring


def configure_sources(pod_substring: str,
                      sources_type: Optional[str] = None) -> None:
    locate_oc(SERVICE_ONECLIENT, pod_substring, generate_pod_name=False,
              sources_type=sources_type)

    log_file_path = os.path.join(deployments_dir.get_current_log_dir(),
                                 'rsync_{}.log'.format(pod_substring))
    deployment_data_cfg = deployment_data.get(default={})
    sources.rsync_sources_for_oc_deployment(pod_substring, deployment_data_cfg,
                                            log_file_path)


def main() -> None:
    oneclient_args_parser = argparse.ArgumentParser(
        prog='onenv oneclient',
        formatter_class=arg_help_formatter.ArgumentsHelpFormatter,
        description='Starts new oneclient deployment.'
    )

    oneclient_args_parser.add_argument(
        help='name of the oneclient deployment that will '
             'be started. Please note that this name should be unique for '
             'each k8s deployment.',
        dest='name'
    )

    oneclient_args_parser.add_argument(
        '-i', '--image',
        help='oneclient image to use'
    )

    oneclient_args_parser.add_argument(
        '-r', '--release_name',
        help='helm release name for oneclient deployment. By default '
             'name of the deployment will be used.',
        dest='release_name'
    )

    oneclient_args_parser.add_argument(
        '-drn', '--deployment-release-name',
        default=user_config.get_current_release_name(),
        help='helm release name of deployment to which oneclient should be '
             'added. By default current release name form one-env config '
             'will be used.',
        dest='deployment_release_name'
    )

    oneclient_args_parser.add_argument(
        '-c', '--config',
        help='path to custom oneclient configuration file.',
    )

    oneclient_args_parser.add_argument(
        '-p', '--provider',
        help='provider pod name (or matching pattern, use "-" for wildcard)',
    )

    oneclient_args_parser.add_argument(
        '-s', '--sources',
        action='store_true',
        help='specifies if pre-compiled sources from host should be used'
    )

    oneclient_args_parser.add_argument(
        '-t', '--sources-type',
        action='store',
        choices=('debug', 'release'),
        help='allows to specify which oneclient binary should be used. '
             'This refers to the mode in which oneclient binary has been '
             'built.',
        dest='sources_type'
    )

    oneclient_args_parser.add_argument(
        '-d', '--direct-io',
        action='store_true',
        help='Need to be set if oneclient will be used in direct-io mode.'
             'Note that this requires NFS storage mounted in oneprovider '
             'service.'
    )

    oneclient_args = oneclient_args_parser.parse_args()
    release_name = oneclient_args.release_name or oneclient_args.name

    pod_substring = start_oneclient_deployment(
        name=oneclient_args.name,
        release_name=release_name,
        deployment_release_name=oneclient_args.deployment_release_name,
        oneclient_cfg_path=oneclient_args.config,
        direct_io=oneclient_args.direct_io,
        provider_substring=oneclient_args.provider,
        image=oneclient_args.image
    )

    if oneclient_args.sources:
        configure_sources(pod_substring, oneclient_args.sources_type)

    user_config.ensure_exists()


if __name__ == '__main__':
    main()
