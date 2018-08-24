"""
Part of onenv tool that allows to patch current deployment
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"


import os
import yaml
import shutil
import argparse
import subprocess

import helm
import pods
import console
import user_config
import argparse_utils
import deployments_dir
import config.writers as writers
import config.readers as readers
from names_and_paths import (CROSS_SUPPORT_JOB_REPO_PATH, CROSS_SUPPORT_JOB,
                             ONEDATA_CHART_REPO, ONEDATA_3P)
from scenario_runner import update_charts_dependencies


SCRIPT_DESCRIPTION = 'Patch onedata deployment.'


def delete_old_support_jobs(release_name):
    cross_support_label = 'app={}-{}'.format(release_name, CROSS_SUPPORT_JOB)
    print(cross_support_label)
    subprocess.call(pods.cmd_delete_jobs(all=False, label=cross_support_label,
                                         include_uninitialized=True))


def parse_global_conf(landscape, release_name):
    global_cfg = landscape.get('global', {})
    global_cfg['releaseNameOverride'] = release_name
    landscape['global'] = global_cfg


def parse_onedata3p_conf(landscape, admin_creds):
    onedata_3p_conf = landscape.get(ONEDATA_3P, {})
    onedata_3p_conf['enabled'] = False

    onezone_conf = onedata_3p_conf.get('onezone', {})
    if not onezone_conf.get('onezoneAdmin'):
        admin_username, admin_password = admin_creds
        onezone_conf['onezoneAdmin'] = {'name': admin_username,
                                        'password': admin_password}
    onedata_3p_conf['onezone'] = onezone_conf
    landscape[ONEDATA_3P] = onedata_3p_conf


def main():
    parser = argparse.ArgumentParser(
        prog='onenv up',
        formatter_class=argparse_utils.ArgumentsHelpFormatter,
        description=SCRIPT_DESCRIPTION
    )

    parser.add_argument(
        '-l', '--landscape_path',
        action='store',
        required=True,
        help='Path to landscape',
        dest='landscape_path')

    parser.add_argument(
        '-lcp', '--local-chart-path',
        action='store',
        help='Path to local charts',
        dest='local_charts_path')

    parser.add_argument(
        '--admin',
        default=['admin', 'password'],
        nargs=2,
        help='admin credentials in form: -u username password',
        metavar=('username', 'password'),
        dest='admin')

    parser.add_argument(
        '-drn', '--deployment-release-name',
        action='store',
        default=user_config.get_current_release_name(),
        help='helm release name of deployment to patch',
        dest='deployment_release_name')

    parser.add_argument(
        '-prn', '--patch-release-name',
        action='store',
        help='helm release name of patch deployment',
        dest='patch_release_name')

    args = parser.parse_args()

    user_config.ensure_exists()
    helm.ensure_deployment(exists=True, fail_with_error=True)

    deployment_dir_path = deployments_dir.current_deployment_dir()
    deployment_charts_path = os.path.join(deployment_dir_path, 'charts')
    deployment_logdir_path = os.path.join(deployment_dir_path, 'logs')
    shutil.copy(args.landscape_path, deployment_dir_path)
    deployment_landscape_path = os.path.join(deployment_dir_path,
                                             os.path.basename(args.landscape_path))
    patch_release_name = (args.patch_release_name if args.patch_release_name
                          else 'patch-{}'.format(args.deployment_release_name))

    helm.clean_deployment(patch_release_name)

    reader = readers.ConfigReader(deployment_landscape_path)
    landscape = reader.load()

    delete_old_support_jobs(args.deployment_release_name)
    parse_onedata3p_conf(landscape, args.admin)
    parse_global_conf(landscape, args.deployment_release_name)

    writer = writers.ConfigWriter(landscape, 'yaml')
    with open(deployment_landscape_path, 'w') as f:
        f.write(writer.dump())

    if args.local_charts_path:
        if os.path.exists(deployment_charts_path):
            shutil.rmtree(deployment_charts_path)
        shutil.copytree(args.local_charts_path, deployment_charts_path)
        update_charts_dependencies(deployment_logdir_path,
                                   deployment_charts_path)
        helm_install_cmd = helm.cmd_install(CROSS_SUPPORT_JOB,
                                            [deployment_landscape_path],
                                            release_name=patch_release_name)
    else:
        console.info('Adding {} repo to helm repositories'.format(
            ONEDATA_CHART_REPO))
        cmd = ['helm', 'repo', 'add', 'onedata', ONEDATA_CHART_REPO]
        subprocess.call(cmd, stdout=None, stderr=subprocess.STDOUT)
        helm_install_cmd = helm.cmd_install(CROSS_SUPPORT_JOB_REPO_PATH,
                                            [deployment_landscape_path],
                                            release_name=patch_release_name)

    subprocess.check_call(helm_install_cmd, cwd=deployment_charts_path,
                          stderr=subprocess.STDOUT)


if __name__ == '__main__':
    main()
