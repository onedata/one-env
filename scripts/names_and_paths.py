"""
Common definitions and defines used in all scripts.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

from os.path import join as join_path
import helm
import pods


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


def gen_pod_name(service, node_name):
    node_num = node_name.split(NODE_NAME)[1]
    return '{}-{}-{}'.format(helm.get_deployment_name(), service, node_num)


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


def service_name_to_alias_mapping(name):
    return [val for key, val in
            {'oneprovider-krakow': 'oneprovider-1',
             'oneprovider-paris': 'oneprovider-2',
             'oneprovider-lisbon': 'oneprovider-3',
             'onezone': 'onezone'}.items() if key.lower() in name][0]


def client_alias_to_pod_mapping():
    prov_clients_mapping = {}
    client_alias_mapping = {}
    pods_list = pods.list_pods()
    clients_pods = [pod for pod in pods_list
                    if pods.get_service_type(pod) == 'oneclient']
    for client_pod in clients_pods:
        provider = pods.get_client_provider_host(client_pod)
        provider_alias = service_name_to_alias_mapping(provider)
        if provider_alias in prov_clients_mapping:
            prov_clients_mapping[provider_alias].append(client_pod)
        else:
            prov_clients_mapping[provider_alias] = [client_pod]

    i = 1
    for prov_alias in sorted(list(prov_clients_mapping.keys())):
        client_pods = sorted(prov_clients_mapping.get(prov_alias),
                             key=pods.get_name)
        for pod in client_pods:
            key = 'oneclient-{}'.format(i)
            client_alias_mapping[key] = pods.get_name(pod)
            client_alias_mapping[pods.get_name(pod)] = key
            i += 1
    return client_alias_mapping
