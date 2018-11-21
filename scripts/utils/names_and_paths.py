"""
Common definitions and defines used in all scripts.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

from typing import Optional
from os.path import join as join_path

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
SERVICE_ONEPROVIDER = 'oneprovider'

NODE_NAME = 'n'

ONEDATA_CHART_REPO = 'https://onedata.github.io/charts/'
CROSS_SUPPORT_JOB = 'cross-support-job-3p'
CROSS_SUPPORT_JOB_REPO_PATH = 'onedata/cross-support-job-3p'
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
    'onezone': 'onezone'
}

SERVICE_AND_APP_TYPE_TO_APP_MAPPING = {
    (SERVICE_ONEZONE, APP_TYPE_WORKER): APP_ONEZONE,
    (SERVICE_ONEZONE, APP_TYPE_PANEL): APP_OZ_PANEL,
    (SERVICE_ONEZONE, APP_TYPE_CLUSTER_MANAGER): APP_CLUSTER_MANAGER,
    (SERVICE_ONEPROVIDER, APP_TYPE_WORKER): APP_ONEPROVIDER,
    (SERVICE_ONEPROVIDER, APP_TYPE_PANEL): APP_OP_PANEL,
    (SERVICE_ONEPROVIDER, APP_TYPE_CLUSTER_MANAGER): APP_CLUSTER_MANAGER
}


def gen_pod_name(service: str, node_name: str) -> str:
    node_num = node_name.split(NODE_NAME)[1]
    return '{}-{}-{}'.format(user_config.get_current_release_name(), service,
                             node_num)


def rel_sources_dir(app: str) -> str:
    return join_path('_build', 'default', 'rel', app.replace('-', '_'))


def rel_start_script_file(app: str) -> str:
    return join_path(rel_sources_dir(app), 'bin', app.replace('-', '_'))


def abs_start_script_file(app: str) -> str:
    return app.replace('-', '_')


def rel_logs_dir(app: str) -> str:
    return join_path(rel_sources_dir(app), 'log')


def abs_logs_dir(app: str) -> str:
    return join_path('/', 'var', 'log', app.replace('-', '_'))


def service_and_app_type_to_app(chart: str, app_type: str) -> str:
    return SERVICE_AND_APP_TYPE_TO_APP_MAPPING[(chart, app_type)]


def service_name_to_alias_mapping(name: str) -> Optional[str]:
    return next((val for key, val in SERVICE_MAPPING.items()
                 if key.lower() in name), None)
