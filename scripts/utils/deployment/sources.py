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
from typing import List, IO, Any, Dict, Optional

import yaml

from .node import Node
from ..k8s import pods
from .. import terminal
from ..one_env_dir import deployment_data
from ..shell import call_and_check_return_code, call
from ..names_and_paths import (SERVICE_ONECLIENT, ONECLIENT_BIN_PATH,
                               get_service_type, rel_etc_dir, abs_etc_dir,
                               rel_logs_dir, abs_logs_dir,
                               abs_mnesia_dir, APP_NAME_TO_APP_TYPE_MAPPING,
                               APP_TYPE_WORKER, APP_TYPE_PANEL,
                               APP_TYPE_CLUSTER_MANAGER, rel_mnesia_dir)


CERT_DIRS = ['certs', 'cacerts']
CONFIG_FILES = ['auth.config', 'overlay.config']
OP_OZ_DIRS_TO_SYNC = ['_build', 'priv', 'src', 'include']
SOURCES_READY_FILE_PATH = '/tmp/sources_ready.txt'

DEFAULT_POD_TIMEOUT = 300

PERSISTENCE_DIR = '/volumes/persistence'
PERSISTENCE_PATHS_FUNCTIONS = {
    APP_TYPE_WORKER: {
        'abs_paths': [abs_etc_dir, abs_logs_dir],
        'rel_paths': [rel_etc_dir, rel_logs_dir]
    },
    APP_TYPE_PANEL: {
        'abs_paths': [abs_etc_dir, abs_logs_dir, abs_mnesia_dir],
        'rel_paths': [rel_etc_dir, rel_logs_dir, rel_mnesia_dir]
    },
    APP_TYPE_CLUSTER_MANAGER: {
        'abs_paths': [abs_etc_dir, abs_logs_dir],
        'rel_paths': [rel_etc_dir, rel_logs_dir]
    }
}


def get_persistence_dirs(app_name: str) -> Dict[str, List[str]]:
    app_type = APP_NAME_TO_APP_TYPE_MAPPING[app_name]
    path_functions = PERSISTENCE_PATHS_FUNCTIONS.get(app_type, {})
    return {'abs_paths': [fun(app_name)
                          for fun in path_functions.get('abs_paths', [])],
            'rel_paths': [fun(app_name)
                          for fun in path_functions.get('rel_paths', [])]}


def create_persistence_symlinks(sources_path: str, pod_name: str,
                                app_name: str, rsync_persistence_dirs: bool,
                                log_file: Optional[IO[Any]] = None) -> None:
    persistence_paths = get_persistence_dirs(app_name)
    src_paths = [os.path.join(PERSISTENCE_DIR, abs_dir_path[1:])
                 for abs_dir_path in persistence_paths['abs_paths']]
    dest_paths = [os.path.join(sources_path, rel_dir_path)
                  for rel_dir_path in persistence_paths['rel_paths']]

    for src_path, dest_path in zip(src_paths, dest_paths):
        if not pods.file_exists_in_pod(pod_name, src_path):
            mkdir_cmd = ['bash', '-c', 'mkdir -p {}'.format(src_path)]
            call(pods.exec_cmd(pod_name, mkdir_cmd))

        if not pods.file_exists_in_pod(pod_name, os.path.dirname(dest_path)):
            mkdir_cmd = ['bash', '-c',
                         'mkdir -p {}'.format(os.path.dirname(dest_path))]
            call(pods.exec_cmd(pod_name, mkdir_cmd))
        pods.create_symlink(pod_name, src_path, dest_path)

        if rsync_persistence_dirs:
            rsync_file(dest_path, pod_name,
                       '{}:{}'.format(pod_name, dest_path), log_file)


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


def is_ready_file_present_in_pod(pod_name: str) -> bool:
    return pods.file_exists_in_pod(pod_name, SOURCES_READY_FILE_PATH)


def create_ready_file_cmd(panel_path: str = None) -> List[str]:
    cmd = ['bash', '-c']

    if panel_path:
        cmd.append('echo {} >> {}'.format(panel_path, SOURCES_READY_FILE_PATH))
    else:
        cmd.append('touch {}'.format(SOURCES_READY_FILE_PATH))

    return cmd


def rsync_file(file_path: str, pod_name: str, pod_dest_path: str,
               log_file: IO[Any], excludes: Optional[List[str]] = None):
    if os.path.isdir(file_path):
        mkdir_cmd = ['bash', '-c', 'mkdir -p {}'.format(file_path)]
        call_and_check_return_code(pods.exec_cmd(pod_name, mkdir_cmd),
                                   stdout=log_file)
    if os.path.exists(file_path):
        call_and_check_return_code(pods.rsync_cmd(file_path, pod_dest_path,
                                                  excludes=excludes),
                                   stdout=log_file)


def rsync_sources_for_app(pod_name: str, sources_path: str, dest_path: str,
                          files_to_rsync: List[str], log_file: IO[Any],
                          excludes: Optional[List[str]] = None) -> None:
    pod_dest_path = '{}:{}'.format(pod_name, dest_path)
    threads = []
    for file_to_sync in files_to_rsync:
        file_path = os.path.join(sources_path, file_to_sync)
        thread = Thread(target=rsync_file, args=(file_path, pod_name,
                                                 pod_dest_path, log_file,
                                                 excludes))
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


def rsync_sources_for_oz_op(pod_name: str, node_cfg: Node,
                            deployment_data_dict: Dict[str, Dict],
                            log_file_path: str, timeout: int,
                            rsync_persistence_dirs: bool = False) -> None:
    pod = pods.match_pods(pod_name)[0]
    pods.wait_for_container(pods.get_service_type(pod), pod_name,
                            timeout=timeout)
    service_name = pods.get_chart_name(pod)
    panel_name = 'oz_panel' if 'zone' in service_name else 'op_panel'
    pod_sources_cfg = deployment_data_dict.get('sources').get(pod_name).items()

    if not is_ready_file_present_in_pod(pod_name):
        terminal.info('Rsyncing sources for pod {}. All logs can be found '
                      'in {}.'.format(pod_name, log_file_path))
        with open(log_file_path, 'w') as log_file:
            panel_from_sources = any('panel' in s for s, _ in pod_sources_cfg)
            panel_path = ''

            for app_name, sources_path in pod_sources_cfg:
                create_persistence_symlinks(sources_path, pod_name, app_name,
                                            rsync_persistence_dirs=rsync_persistence_dirs,
                                            log_file=log_file)
                rsync_sources_for_app(pod_name, sources_path, sources_path,
                                      OP_OZ_DIRS_TO_SYNC, log_file,
                                      excludes=['*/etc', '*/log'])
                if 'panel' in app_name:
                    modify_onepanel_app_config(node_cfg, panel_name, pod_name,
                                               log_file, sources_path)
                    panel_path = sources_path

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
                  nodes_cfg: Dict[str, Dict], timeout: int,
                  rsync_persistence_dirs: bool = False) -> None:
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
                pod = pods.match_pods(pod_substring)[0]
                service_name = pods.get_chart_name(pod)
                node_name = pods.get_node_name(pod_substring)
                node_cfg = nodes_cfg.get(service_name, {}).get(node_name)
                if node_cfg:
                    thread = Thread(target=rsync_sources_for_oz_op,
                                    args=(pod_substring, node_cfg,
                                          deployment_data_dict, log_file_path,
                                          timeout, rsync_persistence_dirs))
                    thread.start()
                    threads.append(thread)

        for thread in threads:
            thread.join()
