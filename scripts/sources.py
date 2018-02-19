"""
Convenience functions that locate precompiled sources to be used in env setup.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

from os.path import join as join_path
from os.path import normpath
import os
import sys
import console
import pods
import deployment_data
from names_and_paths import *


def release_dirs_to_check(app):
    return {
        APP_OZ_PANEL: ['oz-panel', 'oz_panel', 'onepanel'],
        APP_ONEZONE: ['oz-worker', 'oz_worker'],
        APP_OP_PANEL: ['op-panel', 'op_panel', 'onepanel'],
        APP_ONEPROVIDER: ['op-worker', 'op_worker'],
        APP_CLUSTER_MANAGER: ['cluster-manager', 'cluster_manager'],
    }.get(app, [])


def locate(app, service, node_name):
    cwd = os.getcwd()
    dirs_to_check = release_dirs_to_check(app)
    paths_to_check = [join_path(cwd, p) for p in dirs_to_check]
    paths_to_check.extend([join_path(cwd, '../', p) for p in dirs_to_check])
    location = None
    for path in paths_to_check:
        if os.path.isdir(path):
            location = path
            break

    if not location:
        console.error('Cannot locate directory for {}, tried:'.format(
            app))
        for path in paths_to_check:
            console.error('    ' + path)
        sys.exit(1)

    location = normpath(location)

    pod_name = gen_pod_name(service, node_name)
    console.info('{} -> {}: using sources from:\n    {}'.format(
        console.green_str(pod_name),
        console.green_str(app),
        console.green_str(location)))
    precompiled_release_loc = join_path(location,
                                        rel_sources_dir(app))
    if not os.path.isdir(precompiled_release_loc):
        console.error(
            'Cannot locate release dir for {}, tried: {}'.format(
                app, precompiled_release_loc))
        sys.exit(1)

    # Save sources path to deployment data file
    data = deployment_data.get()
    if 'sources' not in data:
        data['sources'] = {}
    if pod_name not in data['sources']:
        data['sources'][pod_name] = {}
    data['sources'][pod_name][app] = location
    deployment_data.put(data)
    return location


def get_sources_path(app, pod_name):
    data = deployment_data.get()
    try:
        return data['sources'][pod_name][app]
    except Exception:
        return None


def start_script_path(app, pod_name):
    bin_path = get_sources_path(app, pod_name)
    if bin_path:
        return join_path(bin_path, rel_start_script_file(app))
    else:
        return abs_start_script_file(app)


def logs_dir(app, pod_name):
    bin_path = get_sources_path(app, pod_name)
    if bin_path:
        return join_path(bin_path, rel_logs_dir(app))
    else:
        return abs_logs_dir(app)


def logs_file(app, pod_name, logfile='info.log'):
    if '.' not in logfile:
        logfile = '{}.log'.format(logfile)
    return join_path(logs_dir(app, pod_name), logfile)
