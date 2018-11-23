"""
Convenience functions that locate precompiled sources to be used in env setup.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import os
import sys
import contextlib
from typing import Optional

from .. import terminal
from ..one_env_dir import deployment_data
from ..names_and_paths import (gen_pod_name, APP_OZ_PANEL, APP_OP_PANEL,
                               APP_ONEPROVIDER, APP_ONEZONE,
                               APP_CLUSTER_MANAGER, join_path, rel_sources_dir,
                               rel_start_script_file, abs_start_script_file,
                               abs_logs_dir, rel_logs_dir)


RELEASE_DIRS_TO_CHECK = {
    APP_OZ_PANEL: ['oz-panel', 'oz_panel', 'onepanel'],
    APP_ONEZONE: ['oz-worker', 'oz_worker'],
    APP_OP_PANEL: ['op-panel', 'op_panel', 'onepanel'],
    APP_ONEPROVIDER: ['op-worker', 'op_worker'],
    APP_CLUSTER_MANAGER: ['cluster-manager', 'cluster_manager'],
}


def locate(app: str, service: str, node_name: str) -> str:
    cwd = os.getcwd()
    dirs_to_check = RELEASE_DIRS_TO_CHECK.get(app, [])
    paths_to_check = [join_path(cwd, p) for p in dirs_to_check]
    paths_to_check.extend([join_path(cwd, '../', p) for p in dirs_to_check])
    paths_to_check.extend([join_path(cwd, '../../', p) for p in dirs_to_check])
    location = next((path for path in paths_to_check if os.path.isdir(path)),
                    None)

    if not location:
        terminal.error('Cannot locate directory for {}, tried:'.format(app))
        for path in paths_to_check:
            terminal.error('    ' + path)
        sys.exit(1)

    location = os.path.normpath(location)

    pod_name = gen_pod_name(service, node_name)
    terminal.info('{} -> {}: using sources from:\n    {}'
                  .format(terminal.green_str(pod_name),
                          terminal.green_str(app),
                          terminal.green_str(location)))
    precompiled_release_loc = join_path(location,
                                        rel_sources_dir(app))
    if not os.path.isdir(precompiled_release_loc):
        terminal.error('Cannot locate release dir for {}, '
                       'tried: {}'.format(app, precompiled_release_loc))
        sys.exit(1)

    # Save sources path to deployment data file
    data = deployment_data.get(default={})
    if 'sources' not in data:
        data['sources'] = {}
    if pod_name not in data['sources']:
        data['sources'][pod_name] = {}
    data['sources'][pod_name][app] = location
    deployment_data.put(data)
    return location


def get_sources_path(app: str, pod_name: str) -> Optional[str]:
    data = deployment_data.get(default={})
    with contextlib.suppress(KeyError):
        return data['sources'][pod_name][app]


def get_start_script_path(app: str, pod_name: str) -> str:
    bin_path = get_sources_path(app, pod_name)
    if bin_path:
        return join_path(bin_path, rel_start_script_file(app))
    return abs_start_script_file(app)


def get_logs_dir(app: str, pod_name: str) -> str:
    bin_path = get_sources_path(app, pod_name)
    if bin_path:
        return join_path(bin_path, rel_logs_dir(app))
    return abs_logs_dir(app)


def get_logs_file(app: str, pod_name: str, logfile: str = 'info.log') -> str:
    if '.' not in logfile:
        logfile = '{}.log'.format(logfile)
    return join_path(get_logs_dir(app, pod_name), logfile)
