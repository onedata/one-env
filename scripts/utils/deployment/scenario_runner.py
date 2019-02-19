"""
Brings up onedata deployment described in given scenario
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import re
import os
import shutil
import subprocess
from typing import Dict

import yaml

from .. import terminal
from ..k8s import helm, pods
from ...onenv_wait import wait
from ..deployment import sources
from ..yaml_utils import load_yaml
from ..one_env_dir import deployment_data
from ..deployment import config_parser, config_generator
from ...onenv_status import deployment_status, user_config
from ..names_and_paths import (CROSS_SUPPORT_JOB_REPO_PATH,
                               CROSS_SUPPORT_JOB,
                               service_name_to_alias_mapping)


CHART_VERSION = '0.2.15-rc1'


def get_scenario_key(sources_val_path: str) -> str:
    sources_val = load_yaml(sources_val_path)

    return next((key for key in sources_val
                 if re.match(r'onedata-\d+p', key)), '')


def update_charts_dependencies(log_directory_path: str,
                               deployment_charts_path: str) -> None:
    make_charts_cmd = ['make', CROSS_SUPPORT_JOB]
    log_file_path = os.path.join(log_directory_path, 'make_charts.log')
    terminal.info('Updating charts dependencies. Writing logs to {}'
                  .format(log_file_path))

    with open(log_file_path, 'w') as log_file:
        subprocess.check_call(make_charts_cmd, cwd=deployment_charts_path,
                              stdout=log_file, stderr=subprocess.STDOUT)


def configure_os(os_configs: Dict[str, Dict], timeout: int) -> None:
    wait(timeout)
    dep_status = yaml.load(deployment_status())
    pods_cfg = dep_status.get('pods')
    ready = dep_status.get('ready')

    if not ready:
        print('Os configuration failed - deployment is not ready')
        exit(1)

    for pod_name, pod_cfg in pods_cfg.items():
        service_type = pod_cfg['service-type']
        if service_type in ['onezone', 'oneprovider']:
            alias = service_name_to_alias_mapping(pod_name)
            os_config = os_configs.get('services').get(alias)
            if os_config:
                pods.wait_for_container(service_type, pod_name)
                pods.create_users(pod_name, os_config.get('users'))
                pods.create_groups(pod_name, os_config.get('groups'))
        if service_type == 'oneclient':
            client_alias = pods.client_alias_to_pod_mapping().get(pod_name)
            os_config = os_configs.get('services').get(client_alias)
            if os_config:
                pods.wait_for_container(service_type, pod_name)
                pods.create_users(pod_name, os_config.get('users'))
                pods.create_groups(pod_name, os_config.get('groups'))


def run_scenario(deployment_dir: str, local_chart_path: str, debug: bool,
                 dry_run: bool, timeout: int) -> None:
    env_cfg = load_yaml(os.path.join(deployment_dir, 'env_config.yaml'))
    original_scenario_path = os.path.join('scenarios', env_cfg.get('scenario'))
    deployment_charts_path = os.path.join(deployment_dir, 'charts')
    deployment_logdir_path = os.path.join(deployment_dir, 'logs')
    deployment_scenario_path = os.path.join(deployment_dir,
                                            original_scenario_path)
    base_sources_cfg_path = os.path.join(deployment_scenario_path,
                                         'SourcesVal.yaml')

    os.mkdir(deployment_logdir_path)
    shutil.copytree(original_scenario_path, deployment_scenario_path)

    my_values_path = os.path.join(deployment_scenario_path, 'MyValues.yaml')
    custom_config_path = os.path.join(deployment_scenario_path,
                                      'CustomConfig.yaml')

    if local_chart_path:
        shutil.copytree(local_chart_path, deployment_charts_path)
        update_charts_dependencies(deployment_logdir_path,
                                   deployment_charts_path)
        helm_install_cmd = helm.install_cmd(CROSS_SUPPORT_JOB,
                                            [my_values_path,
                                             custom_config_path])
    else:
        os.mkdir(deployment_charts_path)
        helm.add_onedata_repo()
        helm_install_cmd = helm.install_cmd(CROSS_SUPPORT_JOB_REPO_PATH,
                                            [my_values_path,
                                             custom_config_path])

    scenario_key = get_scenario_key(base_sources_cfg_path)
    parsed_src_cfg = config_parser.parse_env_config(env_cfg,
                                                    base_sources_cfg_path,
                                                    scenario_key,
                                                    deployment_scenario_path,
                                                    my_values_path)

    # Add debug flags if specified
    if debug:
        helm_install_cmd.extend(['--debug'])
    if dry_run:
        helm_install_cmd.extend(['--dry-run'])

    if env_cfg.get('sources'):
        nodes_cfg = config_generator.generate_configs(parsed_src_cfg,
                                                      base_sources_cfg_path,
                                                      scenario_key,
                                                      deployment_dir)

        helm_install_cmd.extend(['-f', base_sources_cfg_path])

    if not local_chart_path:
        helm_install_cmd.extend(['--version', CHART_VERSION])

    subprocess.check_call(helm_install_cmd,
                          cwd=os.path.join(deployment_charts_path),
                          stderr=subprocess.STDOUT)
    deployment_data.add_release(user_config.get_current_release_name())

    if env_cfg.get('sources'):
        sources.rsync_sources(deployment_dir, deployment_logdir_path,
                              nodes_cfg)

    if env_cfg.get('os-config'):
        configure_os(env_cfg.get('os-config'), timeout)
