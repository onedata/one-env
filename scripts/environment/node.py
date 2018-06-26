import os
import textwrap
import re


def replace(file_path, pattern, value):
    with open(file_path, 'r+') as f:
        content = f.read()
        content = re.sub(pattern, value, content)
        f.seek(0)
        f.truncate()
        f.write(content)


def change_node_app_config(deployment_dir, service_name, node_name, apps):
    panel = 'op-panel' if 'oneprovider' in service_name else 'oz-panel'
    app_config_path = os.path.join(deployment_dir, service_name,
                           '{}-{}-{}-rel'.format(service_name, node_name, panel),
                           'data', 'app.config'.format(node_name))

    for app in apps:
        create_config_for_app(app, app_config_path)


def create_config_for_app(app, path):
    for attr, val in app.config.items():
        if 'panel' not in app.name:
            attr = '{}_{}'.format(app.name, attr)
        else:
            attr = 'onepanel_{}'.format(attr)
        replace(path, r'{{{}, .*}}'.format(attr), r'{{{}, "{}"}}'.format(attr, val))