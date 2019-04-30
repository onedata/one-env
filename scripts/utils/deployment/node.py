"""
This module implements class responsible for holding data about given
node and functions responsible for parsing applications app.config.
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import os
import shutil
from typing import List

from ..k8s import pods
from .application import Application
from ..common import replace_in_file_using_open
from ..one_env_dir import deployment_data, deployments_dir
from ..names_and_paths import (APP_TYPE_PANEL, APP_ONEPANEL, SERVICE_ONEZONE,
                               ONEZONE_APPS, ONEPROVIDER_APPS)


def modify_app_config(app: Application, path: str) -> None:
    attr_fmt = '{}_{{}}'.format(APP_ONEPANEL
                                if APP_TYPE_PANEL in app.name
                                else app.name)
    for attr, val in app.config.items():
        app_attr = attr_fmt.format(attr)
        replace_in_file_using_open(path, r'{{{}, .*}}'.format(app_attr),
                                   r'{{{}, "{}"}}'.format(app_attr, val))


# pylint: disable=too-few-public-methods
class Node:
    def __init__(self, node_name: str, apps: List[Application],
                 service_name: str, deployment_dir: str):
        self.node_name = node_name
        self.apps = apps
        self.service_name = service_name

        self.deployment_dir = deployment_dir
        self.service_dir = os.path.join(deployment_dir, service_name)
        self.rel_dir = os.path.join(self.service_dir, self.node_name)
        self.app_config_path = os.path.join(self.rel_dir, 'app.config')

    def modify_node_app_config(self) -> None:
        panel = next(app for app in self.apps if APP_TYPE_PANEL in app.name)

        # create application's rel dir for current installation
        os.makedirs(self.rel_dir, exist_ok=True)

        # when using panel from sources, we can use its app.config - in
        # the other case we need to get app.config from running pod
        if panel.release_path:
            shutil.copy(os.path.join(panel.release_path, 'data/app.config'),
                        self.rel_dir)

        for app in self.apps:
            modify_app_config(app, self.app_config_path)

    def add_node_to_nodes_cfg(self, nodes_cfg) -> None:
        try:
            nodes_cfg[self.service_name][self.node_name] = self
        except KeyError:
            nodes_cfg[self.service_name] = {self.node_name: self}

    @staticmethod
    def load_node_for_pod_from_deployment_data(pod_name: str,
                                               service_name: str):
        deployment_cfg = deployment_data.get()
        node_name = pods.get_node_name(pod_name)
        pod_cfg = deployment_cfg.get('sources', {}).get(pod_name, {})

        if SERVICE_ONEZONE in service_name:
            service_apps = ONEZONE_APPS
        else:
            service_apps = ONEPROVIDER_APPS

        node_apps = []
        for app_name in service_apps:
            if app_name in pod_cfg.keys():
                path = pod_cfg.get(app_name)
                node_apps.append(Application(app_name, path, ''))
            else:
                node_apps.append(Application(app_name, '', ''))

        return Node(node_name, node_apps, service_name,
                    deployments_dir.get_current_deployment_dir())
