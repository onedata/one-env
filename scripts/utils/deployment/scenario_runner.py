"""
Brings up onedata deployment described in given scenario
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import re
import os
import time
import shutil
import subprocess
from typing import Dict, List, IO, Any

import yaml

from .node import Node
from .. import terminal
from ..k8s import helm, pods
from ...onenv_wait import wait
from ..yaml_utils import load_yaml
from ...onenv_status import deployment_status
from ..deployment import config_parser, config_generator
from ..names_and_paths import (CROSS_SUPPORT_JOB_REPO_PATH,
                               CROSS_SUPPORT_JOB, ONEDATA_CHART_REPO,
                               service_name_to_alias_mapping)


SOURCES_READY_FILE_PATH = '/tmp/sources_ready.txt'
CHART_VERSION = '0.2.13-rc2'
DIRS_TO_SYNC = ['_build', 'priv', 'src', 'include']


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


def rsync_source(pod_name: str, source_path: str, log_file: IO[Any]) -> None:
    destination_path = '{}:{}'.format(pod_name, source_path)
    for dir_to_sync in DIRS_TO_SYNC:
        dir_path = os.path.join(source_path, dir_to_sync)
        mkdir_cmd = ['bash', '-c', 'mkdir -p {}'.format(dir_path)]
        subprocess.call(pods.exec_cmd(pod_name, mkdir_cmd))

        if os.path.exists(dir_path):
            subprocess.call(pods.rsync_cmd(dir_path, destination_path),
                            shell=True, stdout=log_file)


def copy_overlay_cfg(source_name: str, source_path: str,
                     pod_name: str) -> None:
    parsed_source_name = source_name.replace('-', '_')
    overlay_cfg_path = '/etc/{}/overlay.config'.format(parsed_source_name)

    destination_path = os.path.join(source_path,
                                    '_build/default/rel/{}/etc'.format(parsed_source_name))
    cmd = ['bash', '-c', 'cp {} {}'.format(overlay_cfg_path, destination_path)]
    terminal.info('Copying overlay.config from {} to '
                  '{}'.format(overlay_cfg_path, destination_path))
    subprocess.call(pods.exec_cmd(pod_name, cmd))


def modify_package_app_config(pod_name: str, panel_name: str,
                              node_cfg: Node) -> None:
    source_path = '{}:/var/lib/{}/app.config'.format(pod_name,
                                                     panel_name)
    cmd = pods.copy_from_pod_cmd(source_path, node_cfg.app_config_path)
    subprocess.call(cmd)
    node_cfg.modify_node_app_config()
    subprocess.call(pods.rsync_cmd(node_cfg.app_config_path,
                                   os.path.dirname(source_path)),
                    shell=True)


def modify_source_app_config(node_cfg: Node, source_path: str, panel_name: str,
                             pod_name: str) -> None:
    node_cfg.modify_node_app_config()
    host_app_cfg_path = os.path.join(source_path,
                                     '_build/default/rel/{}/data'.format(
                                         panel_name))
    pod_app_cfg_path = '{}:{}'.format(pod_name,
                                      host_app_cfg_path)
    subprocess.call(pods.rsync_cmd(node_cfg.app_config_path,
                                   pod_app_cfg_path),
                    shell=True)


def wait_for_pod(pod_name: str, timeout: int = 60) -> None:
    start_time = time.time()

    while int(time.time() - start_time) <= timeout:
        pod = next((pod for pod in pods.match_pods(pod_name)), None)
        if pod and pods.is_pod_running(pod):
            return
        time.sleep(1)

    terminal.error('Timeout while waiting for pod {} to be present'
                   .format(pod_name))


def create_ready_file_cmd(panel_path: str = None) -> List[str]:
    cmd = ['bash', '-c']

    if panel_path:
        cmd.append('echo {} >> {}'.format(panel_path, SOURCES_READY_FILE_PATH))
    else:
        cmd.append('touch {}'.format(SOURCES_READY_FILE_PATH))

    return cmd


def rsync_sources_for_pod(pod_name: str, nodes_cfg: Dict[str, Dict],
                          deployment_data: Dict[str, Dict],
                          log_file_path: str) -> None:
    wait_for_pod(pod_name)
    pod = pods.match_pods(pod_name)[0]
    service_name = pods.get_chart_name(pod)
    node_name = 'n{}'.format(pods.get_node_num(pod_name))

    panel_name = 'oz_panel' if 'zone' in service_name else 'op_panel'
    node_cfg = nodes_cfg[service_name][node_name]

    pods.wait_for_pod_to_be_running(pod)
    pod_sources_cfg = deployment_data.get('sources').get(pod_name).items()

    terminal.info('Rsyncing sources for pod {}'.format(pod_name))
    with open(log_file_path, 'w') as log_file:
        panel_from_sources = any('panel' in s for s, _ in pod_sources_cfg)
        panel_path = ''

        for source, source_path in pod_sources_cfg:
            rsync_source(pod_name, source_path, log_file)
            copy_overlay_cfg(source, source_path, pod_name)
            if 'panel' in source:
                modify_source_app_config(node_cfg, source_path,
                                         panel_name, pod_name)
                panel_path = source_path

        if not panel_from_sources:
            modify_package_app_config(pod_name, panel_name, node_cfg)
            subprocess.call(pods.exec_cmd(pod_name,
                                          create_ready_file_cmd()))
        else:
            subprocess.call(pods.exec_cmd(pod_name,
                                          create_ready_file_cmd(panel_path)))

        terminal.info('Rsyncing sources for pod {} done'.format(pod_name))


def rsync_sources(deployment_dir: str, log_directory_path: str,
                  nodes_cfg: Dict[str, Dict]) -> None:
    deployment_data_path = os.path.join(deployment_dir, 'deployment_data.yml')

    with open(deployment_data_path, 'r') as deployment_data_file:
        deployment_data = yaml.load(deployment_data_file)
        log_file_path = os.path.join(log_directory_path, 'rsync_up.log')

        for pod_name in deployment_data.get('sources'):
            rsync_sources_for_pod(pod_name, nodes_cfg, deployment_data,
                                  log_file_path)


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
                wait_for_pod(pod_name)
                pods.create_users(pod_name, os_config.get('users'))
                pods.create_groups(pod_name, os_config.get('groups'))
        if service_type == 'oneclient':
            client_alias = pods.client_alias_to_pod_mapping().get(pod_name)
            os_config = os_configs.get('services').get(client_alias)
            if os_config:
                wait_for_pod(pod_name)
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
        terminal.info('Adding {} repo to helm repositories'
                      .format(ONEDATA_CHART_REPO))
        cmd = helm.add_repo_cmd('onedata', ONEDATA_CHART_REPO)
        subprocess.call(cmd, stdout=None, stderr=subprocess.STDOUT)
        helm_install_cmd = helm.install_cmd(CROSS_SUPPORT_JOB_REPO_PATH,
                                            [my_values_path,
                                             custom_config_path])

    base_sources_cfg = load_yaml(base_sources_cfg_path)
    scenario_key = get_scenario_key(base_sources_cfg_path)

    config_parser.parse_env_config(env_cfg, base_sources_cfg, scenario_key,
                                   deployment_scenario_path, my_values_path)

    # Add debug flags if specified
    if debug:
        helm_install_cmd.extend(['--debug'])
    if dry_run:
        helm_install_cmd.extend(['--dry-run'])

    if env_cfg.get('sources'):
        nodes_cfg = config_generator.generate_configs(base_sources_cfg,
                                                      base_sources_cfg_path,
                                                      scenario_key,
                                                      deployment_dir)

        helm_install_cmd.extend(['-f', base_sources_cfg_path])

    if not local_chart_path:
        helm_install_cmd.extend(['--version', CHART_VERSION])

    subprocess.check_call(helm_install_cmd,
                          cwd=os.path.join(deployment_charts_path),
                          stderr=subprocess.STDOUT)

    if env_cfg.get('sources'):
        rsync_sources(deployment_dir, deployment_logdir_path, nodes_cfg)

    if env_cfg.get('os-config'):
        configure_os(env_cfg.get('os-config'), timeout)
