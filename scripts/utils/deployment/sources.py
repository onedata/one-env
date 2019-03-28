"""
This module contains functions that allows to rsync sources to pods and
that allows to appropriately configure services to run from sources.
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"


import os
from itertools import chain
from threading import Thread
from typing import List, IO, Any, Dict

import yaml

from .node import Node
from ..k8s import pods
from .. import terminal
from ..one_env_dir import deployment_data
from ..shell import call_and_check_return_code
from ..names_and_paths import (SERVICE_ONECLIENT, ONECLIENT_BIN_PATH,
                               get_service_type, rel_etc_dir, abs_etc_dir,
                               APP_ONEZONE)


CERT_DIRS = ['certs', 'cacerts']
CONFIG_FILES = ['auth.config', 'overlay.config']
OP_OZ_DIRS_TO_SYNC = ['_build', 'priv', 'src', 'include']
SOURCES_READY_FILE_PATH = '/tmp/sources_ready.txt'

DEFAULT_POD_TIMEOUT = 300


def modify_onepanel_app_config(node_cfg: Node, panel_name: str, pod_name: str,
                               log_file: IO[Any],
                               sources_path: str = None) -> None:
    if sources_path is not None:
        host_app_cfg_path = os.path.join(sources_path,
                                         '_build/default/rel/{}/data'.format(
                                             panel_name))
        pod_app_cfg_path = '{}:{}'.format(pod_name,
                                          host_app_cfg_path)
    else:
        pod_app_cfg_path = '{}:/var/lib/{}/app.config'.format(pod_name,
                                                              panel_name)
        cmd = pods.copy_from_pod_cmd(pod_app_cfg_path,
                                     node_cfg.app_config_path)
        call_and_check_return_code(cmd, stdout=log_file)
        pod_app_cfg_path = os.path.dirname(pod_app_cfg_path)

    node_cfg.modify_node_app_config()
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


def copy_within_pod(pod_name: str, from_path: str, to_path: str,
                    log_file: IO[Any], is_directory: bool = False):
    if pods.file_exists_in_pod(pod_name, from_path):
        cmd = ['bash', '-c']
        recursive_opt = '-r' if is_directory else ''
        cmd.append('cp {} {} {}'.format(recursive_opt, from_path, to_path))

        terminal.info('Copying {} to {} on pod {}'
                      .format(from_path, to_path, pod_name))
        call_and_check_return_code(pods.exec_cmd(pod_name, cmd),
                                   stdout=log_file)
    else:
        log_file.write('Skipping copying file {} as it does not exists in '
                       'pod.\n'.format(from_path))


def copy_certs(app_name: str, sources_path: str, pod_name: str,
               log_file: IO[Any]) -> None:
    for cert_dir in CERT_DIRS:
        original_path = os.path.join(abs_etc_dir(app_name), cert_dir)
        destination_path = os.path.join(sources_path, rel_etc_dir(app_name))
        copy_within_pod(pod_name, original_path, destination_path, log_file,
                        is_directory=True)


def copy_overlay_cfg(app_name: str, sources_path: str,
                     pod_name: str, log_file: IO[Any]) -> None:
    original_path = os.path.join(abs_etc_dir(app_name), 'overlay.config')
    destination_path = os.path.join(sources_path, rel_etc_dir(app_name))
    copy_within_pod(pod_name, original_path, destination_path, log_file)


def copy_auth_cfg(app_name: str, sources_path: str,
                  pod_name: str, log_file: IO[Any]):
    original_path = os.path.join(abs_etc_dir(app_name), 'auth.config')
    destination_path = os.path.join(sources_path, rel_etc_dir(app_name))
    copy_within_pod(pod_name, original_path, destination_path, log_file)


def rsync_file(file_path: str, pod_name: str, pod_dest_path: str,
               log_file: IO[Any]):
    if os.path.isdir(file_path):
        mkdir_cmd = ['bash', '-c', 'mkdir -p {}'.format(file_path)]
        call_and_check_return_code(pods.exec_cmd(pod_name, mkdir_cmd),
                                   stdout=log_file)
    if os.path.exists(file_path):
        call_and_check_return_code(pods.rsync_cmd(file_path, pod_dest_path),
                                   stdout=log_file)


def rsync_sources_for_app(pod_name: str, sources_path: str, dest_path: str,
                          files_to_rsync: List[str], log_file: IO[Any]) -> None:
    pod_dest_path = '{}:{}'.format(pod_name, dest_path)
    threads = []
    for file_to_sync in files_to_rsync:
        file_path = os.path.join(sources_path, file_to_sync)
        thread = Thread(target=rsync_file, args=(file_path, pod_name,
                                                 pod_dest_path, log_file))
        thread.start()
        threads.append(thread)
    if not files_to_rsync:
        file_path = sources_path
        rsync_file(file_path, pod_name, pod_dest_path, log_file)

    for thread in threads:
        thread.join()


def rsync_sources_for_oc_pod(pod_name: str, pod_sources_cfg: Dict[str, Any],
                             log_file_path: str,
                             timeout: int = DEFAULT_POD_TIMEOUT) -> None:
    with open(log_file_path, 'w') as log_file:
        pods.wait_for_container(SERVICE_ONECLIENT, pod_name,
                                timeout=timeout)
        terminal.info('Rsyncing sources for pod {}'.format(pod_name))
        for sources_path in pod_sources_cfg.values():
            rsync_sources_for_app(pod_name, sources_path, ONECLIENT_BIN_PATH,
                                  [], log_file)
            with deployment_data.DEPLOYMENT_DATA_LOCK:
                deployment_data.add_source(pod_name, SERVICE_ONECLIENT,
                                           sources_path)
        call_and_check_return_code(pods.exec_cmd(pod_name,
                                                 create_ready_file_cmd()),
                                   stdout=log_file)
        terminal.info('Rsyncing sources for pod {} done'
                      .format(pod_name))


def rsync_sources_for_oc_deployment(pod_substring: str,
                                    deployment_data_dict: Dict[str, Dict],
                                    log_file_path: str,
                                    timeout: int = DEFAULT_POD_TIMEOUT) -> None:
    pod_list = [pod for pod in pods.match_pods(pod_substring)
                if not pods.get_deletion_timestamp(pod)]
    pod_sources_cfg = deployment_data_dict.get('oc-deployments').get(pod_substring)
    threads = []
    for pod in pod_list:
        thread = Thread(target=rsync_sources_for_oc_pod,
                        args=(pods.get_name(pod), pod_sources_cfg,
                              log_file_path, timeout))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()


def rsync_sources_for_oz_op(pod_name: str, nodes_cfg: Dict[str, Dict],
                            deployment_data_dict: Dict[str, Dict],
                            log_file_path: str, service_type: str,
                            timeout: int) -> None:
    pods.wait_for_container(service_type, pod_name,
                            timeout=timeout)
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

        for app_name, sources_path in pod_sources_cfg:
            rsync_sources_for_app(pod_name, sources_path, sources_path,
                                  OP_OZ_DIRS_TO_SYNC, log_file)
            copy_overlay_cfg(app_name, sources_path, pod_name, log_file)
            if 'panel' in app_name:
                modify_onepanel_app_config(node_cfg, panel_name, pod_name,
                                           log_file, sources_path)
                panel_path = sources_path
                copy_certs(app_name, sources_path, pod_name, log_file)
            if app_name == APP_ONEZONE:
                copy_auth_cfg(app_name, sources_path, pod_name, log_file)

        if not panel_from_sources:
            modify_onepanel_app_config(node_cfg, panel_name, pod_name,
                                       log_file)
            call_and_check_return_code(pods.exec_cmd(pod_name,
                                                     create_ready_file_cmd()),
                                       stdout=log_file)
        else:
            call_and_check_return_code(
                pods.exec_cmd(pod_name, create_ready_file_cmd(panel_path)),
                stdout=log_file)
        terminal.info('Rsyncing sources for pod {} done'.format(pod_name))


def rsync_sources(deployment_dir: str, log_directory_path: str,
                  nodes_cfg: Dict[str, Dict], timeout: int) -> None:
    deployment_data_path = os.path.join(deployment_dir, 'deployment_data.yml')
    with open(deployment_data_path, 'r') as deployment_data_file:
        deployment_data_dict = yaml.load(deployment_data_file)
        threads = []
        for pod_substring in chain(deployment_data_dict.get('sources', {}),
                                   deployment_data_dict.get('oc-deployments', {})):
            log_file_path = os.path.join(log_directory_path,
                                         '{}_rsync.log'.format(pod_substring))
            service_type = get_service_type(pod_substring)
            if service_type == SERVICE_ONECLIENT:
                thread = Thread(target=rsync_sources_for_oc_deployment,
                                args=(pod_substring, deployment_data_dict,
                                      log_file_path, timeout))
                thread.start()
                threads.append(thread)
            else:
                thread = Thread(target=rsync_sources_for_oz_op,
                                args=(pod_substring, nodes_cfg,
                                      deployment_data_dict, log_file_path,
                                      service_type, timeout))
                thread.start()
                threads.append(thread)

        for thread in threads:
            thread.join()
