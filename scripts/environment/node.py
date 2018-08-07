import os
import re
import shutil

import environment.application as application


def replace(file_path: str, pattern: str, value: str):
    with open(file_path, 'r+') as f:
        content = f.read()
        content = re.sub(pattern, value, content)
        f.seek(0)
        f.truncate()
        f.write(content)


def modify_app_config(app: application.Application, path: str):
    for attr, val in app.config.items():
        if 'panel' not in app.name:
            attr = '{}_{}'.format(app.name, attr)
        else:
            attr = 'onepanel_{}'.format(attr)
        replace(path, r'{{{}, .*}}'.format(attr),
                r'{{{}, "{}"}}'.format(attr, val))


class Node:
    def __init__(self, node_name: str, apps: list, service_name: str,
                 deployment_dir: str):
        self.node_name = node_name
        self.apps = apps
        self.service_name = service_name

        self.deployment_dir = deployment_dir
        self.service_dir = os.path.join(deployment_dir, service_name)
        self.rel_dir = os.path.join(self.service_dir, self.node_name)
        self.app_config_path = os.path.join(self.rel_dir, 'app.config')

    def modify_node_app_config(self):
        panel = [app for app in self.apps if 'panel' in app.name][0]

        # create application's rel dir for current installation
        if not os.path.isdir(self.rel_dir):
            os.makedirs(self.rel_dir, exist_ok=True)

        # when using panel from sources, we can use its app.config - in
        # the other case we need to get app.config from running pod
        if panel.release_path:
            shutil.copy(os.path.join(panel.release_path, 'data/app.config'),
                        self.rel_dir)

        for app in self.apps:
            if app.release_path:
                modify_app_config(app, self.app_config_path)
