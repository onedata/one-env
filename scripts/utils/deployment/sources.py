"""
.
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"


import os
import subprocess
from multiprocessing import Process
from typing import List, IO, Any, Dict

import yaml

from .node import Node
from ..k8s import pods
from .. import terminal, shell
from ..one_env_dir import deployment_data
from ..names_and_paths import (SERVICE_ONECLIENT, ONECLIENT_BIN_PATH,
                               get_service_type)


OP_OZ_DIRS_TO_SYNC = ['_build', 'priv', 'src', 'include']
SOURCES_READY_FILE_PATH = '/tmp/sources_ready.txt'

WAIT_FOR_POD_TIMEOUT = 300


def call_and_check_return_code(cmd: List[str],
                               stdout: shell.File = subprocess.DEVNULL) -> int:

    ret = shell.check_return_code(cmd, stdout=stdout)
    if ret != 0:
        terminal.error('Error in command: {}. More information in logs'
                       'file.'.format(cmd))
    return ret


def modify_package_app_config(pod_name: str, panel_name: str,
                              node_cfg: Node, log_file: IO[Any]) -> None:
    source_path = '{}:/var/lib/{}/app.config'.format(pod_name,
                                                     panel_name)
    cmd = pods.copy_from_pod_cmd(source_path, node_cfg.app_config_path)
    call_and_check_return_code(cmd, stdout=log_file)
    node_cfg.modify_node_app_config()
    call_and_check_return_code(pods.rsync_cmd(node_cfg.app_config_path,
                                              os.path.dirname(source_path)),
                               stdout=log_file)


def modify_source_app_config(node_cfg: Node, source_path: str, panel_name: str,
                             pod_name: str, log_file: IO[Any]) -> None:
    node_cfg.modify_node_app_config()
    host_app_cfg_path = os.path.join(source_path,
                                     '_build/default/rel/{}/data'.format(
                                         panel_name))
    pod_app_cfg_path = '{}:{}'.format(pod_name,
                                      host_app_cfg_path)
    call_and_check_return_code(pods.rsync_cmd(node_cfg.app_config_path,
                                              pod_app_cfg_path),
                               stdout=log_file)


def create_ready_file_cmd(panel_path: str = None) -> List[str]:
    cmd = ['bash', '-c']

    if panel_path:
        cmd.append('echo {} >> {}'.format(panel_path, SOURCES_READY_FILE_PATH))
    else:
        cmd.append('touch {}'.format(SOURCES_READY_FILE_PATH))

    return cmd


def copy_overlay_cfg(source_name: str, source_path: str,
                     pod_name: str, log_file: IO[Any]) -> None:
    parsed_source_name = source_name.replace('-', '_')
    overlay_cfg_path = '/etc/{}/overlay.config'.format(parsed_source_name)

    if pods.file_exists_in_pod(pod_name, overlay_cfg_path):
        destination_path = os.path.join(source_path,
                                        '_build/default/rel/{}/etc'
                                        .format(parsed_source_name))
        cmd = ['bash', '-c', 'cp {} {}'.format(overlay_cfg_path,
                                               destination_path)]

        terminal.info('Copying overlay.config from {} to '
                      '{}'.format(overlay_cfg_path, destination_path))

        call_and_check_return_code(pods.exec_cmd(pod_name, cmd),
                                   stdout=log_file)


def rsync_source(pod_name: str, source_path: str, dest_path: str,
                 files_to_rsync: List[str], log_file: IO[Any]) -> None:
    pod_dest_path = '{}:{}'.format(pod_name, dest_path)

    def rsync_file():
        if os.path.isdir(file_path):
            mkdir_cmd = ['bash', '-c', 'mkdir -p {}'.format(file_path)]
            call_and_check_return_code(pods.exec_cmd(pod_name, mkdir_cmd),
                                       stdout=log_file)
        if os.path.exists(file_path):
            call_and_check_return_code(
                pods.rsync_cmd(file_path, pod_dest_path),
                stdout=log_file)

    processes = []
    if files_to_rsync:
        for file_to_sync in files_to_rsync:
            file_path = os.path.join(source_path, file_to_sync)
            process = Process(target=rsync_file)
            process.start()
            processes.append(process)
    else:
        file_path = source_path
        rsync_file()

    for process in processes:
        process.join()


def rsync_sources_for_oc(pod_substring: str,
                         deployment_data_dict: Dict[str, Dict],
                         log_file_path: str) -> None:
    pods.wait_for_pods_to_be_running(pod_substring,
                                     timeout=WAIT_FOR_POD_TIMEOUT)
    pod_list = pods.match_pods(pod_substring)
    pod_sources_cfg = deployment_data_dict.get('sources').get(pod_substring)

    for pod in pod_list:
        with open(log_file_path, 'w') as log_file:
            pod_name = pods.get_name(pod)

            terminal.info('Rsyncing sources for pod {}'.format(pod_name))
            for source_path in pod_sources_cfg.values():
                rsync_source(pod_name, source_path, ONECLIENT_BIN_PATH,
                             [], log_file)
                deployment_data.add_source(pod_name, SERVICE_ONECLIENT,
                                           source_path)
            call_and_check_return_code(pods.exec_cmd(pod_name,
                                                     create_ready_file_cmd()),
                                       stdout=log_file)
            terminal.info('Rsyncing sources for pod {} done'
                          .format(pod_name))


def rsync_sources_for_oz_op(pod_name: str, nodes_cfg: Dict[str, Dict],
                            deployment_data_dict: Dict[str, Dict],
                            log_file_path: str) -> None:
    pods.wait_for_pods_to_be_running(pod_name, timeout=WAIT_FOR_POD_TIMEOUT)
    pod = pods.match_pods(pod_name)[0]
    service_name = pods.get_chart_name(pod)
    node_name = 'n{}'.format(pods.get_node_num(pod_name))
    panel_name = 'oz_panel' if 'zone' in service_name else 'op_panel'
    node_cfg = nodes_cfg[service_name][node_name]
    pod_sources_cfg = deployment_data_dict.get('sources').get(pod_name).items()

    terminal.info('Rsyncing sources for pod {}. All logs can be found in {}.'
                  .format(pod_name, log_file_path))
    with open(log_file_path, 'w') as log_file:
        panel_from_sources = any('panel' in s for s, _ in pod_sources_cfg)
        panel_path = ''

        for source, source_path in pod_sources_cfg:
            rsync_source(pod_name, source_path, source_path,
                         OP_OZ_DIRS_TO_SYNC, log_file)
            copy_overlay_cfg(source, source_path, pod_name, log_file)
            if 'panel' in source:
                modify_source_app_config(node_cfg, source_path,
                                         panel_name, pod_name, log_file)
                panel_path = source_path

        if not panel_from_sources:
            modify_package_app_config(pod_name, panel_name, node_cfg, log_file)
            call_and_check_return_code(pods.exec_cmd(pod_name,
                                                     create_ready_file_cmd()),
                                       stdout=log_file)
        else:
            call_and_check_return_code(
                pods.exec_cmd(pod_name, create_ready_file_cmd(panel_path)),
                stdout=log_file)
        terminal.info('Rsyncing sources for pod {} done'.format(pod_name))


def rsync_sources(deployment_dir: str, log_directory_path: str,
                  nodes_cfg: Dict[str, Dict]) -> None:
    deployment_data_path = os.path.join(deployment_dir, 'deployment_data.yml')

    with open(deployment_data_path, 'r') as deployment_data_file:
        deployment_data_dict = yaml.load(deployment_data_file)
        processes = []
        for pod_substring in deployment_data_dict.get('sources'):
            log_file_path = os.path.join(log_directory_path,
                                         '{}_rsync.log'.format(pod_substring))
            service_type = get_service_type(pod_substring)
            if service_type == SERVICE_ONECLIENT:
                process = Process(target=rsync_sources_for_oc,
                                  args=(pod_substring, deployment_data_dict,
                                        log_file_path))
                process.start()
                processes.append(process)
            else:
                process = Process(target=rsync_sources_for_oz_op,
                                  args=(pod_substring, nodes_cfg,
                                        deployment_data_dict, log_file_path))
                process.start()
                processes.append(process)

        for process in processes:
            process.join()
