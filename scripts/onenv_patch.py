"""
Part of onenv tool that allows to patch current deployment
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import os
import shutil
import argparse
import subprocess
from typing import Dict, List

from .utils.k8s import helm, pods
from .utils import terminal, arg_help_formatter, yaml_utils
from .utils.one_env_dir import user_config, deployments_dir
from .utils.deployment.scenario_runner import update_charts_dependencies
from .utils.deployment.config_parser import (parse_spaces_cfg,
                                             parse_users_config,
                                             parse_groups_config)
from .utils.names_and_paths import (CROSS_SUPPORT_JOB_REPO_PATH,
                                    CROSS_SUPPORT_JOB, ONEDATA_CHART_REPO,
                                    ONEDATA_3P)


def delete_old_support_jobs(release_name: str) -> None:
    cross_support_label = 'app={}-{}'.format(release_name, CROSS_SUPPORT_JOB)
    subprocess.call(pods.delete_kube_object_cmd('jobs', delete_all=False,
                                                label=cross_support_label,
                                                include_uninitialized=True))


def parse_global_conf(patch: Dict[str, Dict], release_name: str) -> None:
    global_cfg = patch.get('global', {})
    global_cfg['releaseNameOverride'] = release_name
    patch['global'] = global_cfg


def parse_onedata3p_conf(patch: Dict[str, Dict],
                         admin_creds: List[str]) -> None:
    onedata_3p_conf = patch.get(ONEDATA_3P, {})
    onedata_3p_conf['enabled'] = False

    onezone_conf = onedata_3p_conf.get('onezone', {})
    if not onezone_conf.get('onezoneAdmin'):
        admin_username, admin_password = admin_creds
        onezone_conf['onezoneAdmin'] = {'name': admin_username,
                                        'password': admin_password}
    onedata_3p_conf['onezone'] = onezone_conf
    patch[ONEDATA_3P] = onedata_3p_conf


def patch_deployment(patch: str, patch_release_name: str,
                     deployment_release_name: str, local_charts_path: str,
                     admin: List[str]) -> None:
    deployment_dir_path = deployments_dir.get_current_deployment_dir()
    deployment_charts_path = os.path.join(deployment_dir_path, 'charts')
    deployment_logdir_path = os.path.join(deployment_dir_path, 'logs')
    shutil.copy(patch, deployment_dir_path)
    deployment_patch_path = os.path.join(deployment_dir_path,
                                         os.path.basename(patch))
    patch_release_name = (patch_release_name if patch_release_name
                          else 'patch-{}'.format(deployment_release_name))

    helm.clean_deployment(patch_release_name)

    landscape = yaml_utils.load_yaml(deployment_patch_path)

    delete_old_support_jobs(deployment_release_name)
    parse_onedata3p_conf(landscape, admin)
    parse_global_conf(landscape, deployment_release_name)

    parse_groups_config(landscape.get('groups'), landscape)
    parse_users_config(landscape.get('users'), landscape, True)
    parse_spaces_cfg(landscape.get('spaces'), landscape)

    yaml_utils.dump_yaml(landscape, deployment_patch_path)

    if local_charts_path:
        if os.path.exists(deployment_charts_path):
            shutil.rmtree(deployment_charts_path)
        shutil.copytree(local_charts_path, deployment_charts_path)
        update_charts_dependencies(deployment_logdir_path,
                                   deployment_charts_path)
        helm_install_cmd = helm.install_cmd(CROSS_SUPPORT_JOB,
                                            [deployment_patch_path],
                                            release_name=patch_release_name)
    else:
        terminal.info('Adding {} repo to helm repositories'
                      .format(ONEDATA_CHART_REPO))
        subprocess.call(helm.add_repo_cmd('onedata', ONEDATA_CHART_REPO),
                        stdout=None, stderr=subprocess.STDOUT)
        helm_install_cmd = helm.install_cmd(CROSS_SUPPORT_JOB_REPO_PATH,
                                            [deployment_patch_path],
                                            release_name=patch_release_name)

    subprocess.check_call(helm_install_cmd, cwd=deployment_charts_path,
                          stderr=subprocess.STDOUT)


def main() -> None:
    patch_args_parser = argparse.ArgumentParser(
        prog='onenv patch',
        formatter_class=arg_help_formatter.ArgumentsHelpFormatter,
        description='Patch onedata deployment.'
    )

    patch_args_parser.add_argument(
        '-p', '--patch',
        action='store',
        required=True,
        help='Path to patch configuration',
        dest='patch'
    )

    patch_args_parser.add_argument(
        '-lcp', '--local-chart-path',
        action='store',
        help='Path to local charts',
        dest='local_charts_path'
    )

    patch_args_parser.add_argument(
        '--admin',
        default=['admin', 'password'],
        nargs=2,
        help='admin credentials in form: -u username password',
        metavar=('username', 'password'),
        dest='admin'
    )

    patch_args_parser.add_argument(
        '-drn', '--deployment-release-name',
        action='store',
        default=user_config.get_current_release_name(),
        help='helm release name of deployment to patch',
        dest='deployment_release_name'
    )

    patch_args_parser.add_argument(
        '-prn', '--patch-release-name',
        action='store',
        help='helm release name of patch deployment',
        dest='patch_release_name'
    )

    patch_args = patch_args_parser.parse_args()

    user_config.ensure_exists()
    helm.ensure_deployment(exists=True, fail_with_error=True)

    patch_deployment(patch_args.path, patch_args.patch_release_name,
                     patch_args.deployment_release_name, patch_args.local_charts_path,
                     patch_args.admin)


if __name__ == '__main__':
    main()
