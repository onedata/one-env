"""
Common definitions and defines used in all scripts.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import sys
from typing import Optional, List
from os.path import join as join_path

from .terminal import error
from .one_env_dir import user_config


APP_ONEPANEL = 'onepanel'
APP_OZ_PANEL = 'oz-panel'
APP_ONEZONE = 'oz-worker'
APP_OP_PANEL = 'op-panel'
APP_ONEPROVIDER = 'op-worker'
APP_CLUSTER_MANAGER = 'cluster-manager'

APP_TYPE_WORKER = 'worker'
APP_TYPE_PANEL = 'panel'
APP_TYPE_CLUSTER_MANAGER = 'cluster-manager'

SERVICE_ONEZONE = 'onezone'
SERVICE_ONECLIENT = 'oneclient'
SERVICE_ONEPROVIDER = 'oneprovider'

NODE_NAME = 'n'

ONEDATA_CHART_REPO = 'https://onedata.github.io/charts/'
CROSS_SUPPORT_JOB = 'cross-support-job-3p'
CROSS_SUPPORT_JOB_REPO_PATH = 'onedata/cross-support-job-3p'
ONECLIENT_CHART_REPO_PATH = 'onedata/oneclient'
ONEDATA_3P = 'onedata-3p'

ONEZONE_APPS = {APP_OZ_PANEL, APP_CLUSTER_MANAGER, APP_ONEZONE}
ONEPROVIDER_APPS = {APP_OP_PANEL, APP_CLUSTER_MANAGER, APP_ONEPROVIDER}

SERVICE_MAPPING = {
    'oneprovider-krakow': 'oneprovider-1',
    'oneprovider-paris': 'oneprovider-2',
    'oneprovider-lisbon': 'oneprovider-3',
    'oneprovider-1': 'oneprovider-krakow',
    'oneprovider-2': 'oneprovider-paris',
    'oneprovider-3': 'oneprovider-lisbon',
    'oneclient-1': 'oneclient-krakow',
    'oneclient-2': 'oneclient-paris',
    'oneclient-3': 'oneclient-lisbon',
    'oneclient-krakow': 'oneclient-1',
    'oneclient-paris': 'oneclient-2',
    'oneclient-lisbon': 'oneclient-3',
    'onezone': 'onezone'
}


SERVICE_TYPES = [SERVICE_ONEZONE, SERVICE_ONEPROVIDER, SERVICE_ONECLIENT]


SERVICE_AND_APP_TYPE_TO_APP_MAPPING = {
    (SERVICE_ONEZONE, APP_TYPE_WORKER): APP_ONEZONE,
    (SERVICE_ONEZONE, APP_TYPE_PANEL): APP_OZ_PANEL,
    (SERVICE_ONEZONE, APP_TYPE_CLUSTER_MANAGER): APP_CLUSTER_MANAGER,
    (SERVICE_ONEPROVIDER, APP_TYPE_WORKER): APP_ONEPROVIDER,
    (SERVICE_ONEPROVIDER, APP_TYPE_PANEL): APP_OP_PANEL,
    (SERVICE_ONEPROVIDER, APP_TYPE_CLUSTER_MANAGER): APP_CLUSTER_MANAGER
}


APP_NAME_TO_APP_TYPE_MAPPING = {
    APP_ONEZONE: APP_TYPE_WORKER,
    APP_ONEPROVIDER: APP_TYPE_WORKER,
    APP_OP_PANEL: APP_TYPE_PANEL,
    APP_OZ_PANEL: APP_TYPE_PANEL,
    APP_CLUSTER_MANAGER: APP_CLUSTER_MANAGER
}


ONECLIENT_BIN_PATH = '/opt/oneclient/bin'


def gen_pod_name(service: str, service_type: str,
                 node_name: Optional[str] = '') -> str:
    if service_type == SERVICE_ONECLIENT:
        return '{}-{}'.format(user_config.get_current_release_name(),
                              service)
    node_num = node_name.split(NODE_NAME)[1]
    return '{}-{}-{}'.format(user_config.get_current_release_name(),
                             service, node_num)


def oneclient_sources_dirs(sources_type: Optional[str] = None) -> List[str]:
    sources_dirs = []
    if sources_type:
        if sources_type in ('rel', 'release'):
            sources_dirs.append('release')
        elif sources_type in ('deb', 'debug'):
            sources_dirs.append('debug')
        else:
            error('Could not recognize provided type of oneclient sources.'
                  'Possible values are following:\n'
                  '    - for release: rel or release\n'
                  '    - for debug:   deb or debug\n'
                  'Provided value is: {}'.format(sources_type))
            sys.exit(1)
    else:
        sources_dirs.extend(['release', 'debug'])
    return sources_dirs


def rel_sources_dir(app: str) -> str:
    return join_path('_build', 'default', 'rel', app.replace('-', '_'))


def rel_start_script_file(app: str) -> str:
    return join_path(rel_sources_dir(app), 'bin', app.replace('-', '_'))


def abs_start_script_file(app: str) -> str:
    return app.replace('-', '_')


def rel_logs_dir(app: str) -> str:
    return join_path(rel_sources_dir(app), 'log')


def rel_etc_dir(app: str) -> str:
    return join_path(rel_sources_dir(app), 'etc')


def rel_mnesia_dir(app: str) -> str:
    return join_path(rel_sources_dir(app), 'data', 'mnesia')


def abs_etc_dir(app: str) -> str:
    return join_path('/', 'etc', app.replace('-', '_'))


def abs_logs_dir(app: str) -> str:
    return join_path('/', 'var', 'log', app.replace('-', '_'))


def abs_mnesia_dir(app: str) -> str:
    return join_path('/', 'var', 'lib', app.replace('-', '_'), 'mnesia')


def service_and_app_type_to_app(chart: str, app_type: str) -> str:
    return SERVICE_AND_APP_TYPE_TO_APP_MAPPING[(chart, app_type)]


def service_name_to_alias_mapping(name: str) -> Optional[str]:
    return next((val for key, val in SERVICE_MAPPING.items()
                 if key.lower() in name), None)


def get_service_type(service_name: str) -> Optional[str]:
    return next((service_type for service_type in SERVICE_TYPES
                 if service_type.lower() in service_name), None)


def get_matching_oneclient(provider_name: str) -> str:
    return provider_name.replace(SERVICE_ONEPROVIDER, SERVICE_ONECLIENT)


def get_matching_oneprovider(provider_name: str) -> str:
    return provider_name.replace(SERVICE_ONECLIENT, SERVICE_ONEPROVIDER)
