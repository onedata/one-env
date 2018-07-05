"""
Common definitions and defines used in all scripts.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

from os.path import join as join_path
import helm

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


def gen_pod_name(service, node_name):
    node_num = node_name.split(NODE_NAME)[1]
    return '{}-{}-{}'.format(helm.deployment_name(), service, node_num)


def rel_sources_dir(app):
    return join_path('_build', 'default', 'rel', app.replace('-', '_'))


def rel_start_script_file(app):
    return join_path(rel_sources_dir(app), 'bin', app.replace('-', '_'))


def abs_start_script_file(app):
    return app.replace('-', '_')


def rel_logs_dir(app):
    return join_path(rel_sources_dir(app), 'log')


def abs_logs_dir(app):
    return join_path('/', 'var', 'log', app.replace('-', '_'))


def service_and_app_type_to_app(chart, app_type):
    return {
        (SERVICE_ONEZONE, APP_TYPE_WORKER): APP_ONEZONE,
        (SERVICE_ONEZONE, APP_TYPE_PANEL): APP_OZ_PANEL,
        (SERVICE_ONEZONE, APP_TYPE_CLUSTER_MANAGER): APP_CLUSTER_MANAGER,
        (SERVICE_ONEPROVIDER, APP_TYPE_WORKER): APP_ONEPROVIDER,
        (SERVICE_ONEPROVIDER, APP_TYPE_PANEL): APP_OP_PANEL,
        (SERVICE_ONEPROVIDER, APP_TYPE_CLUSTER_MANAGER): APP_CLUSTER_MANAGER
    }[(chart, app_type)]