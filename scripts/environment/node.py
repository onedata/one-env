import os
import textwrap
import re
import shutil


def replace(file_path, pattern, value):
    with open(file_path, 'r+') as f:
        content = f.read()
        content = re.sub(pattern, value, content)
        f.seek(0)
        f.truncate()
        f.write(content)


def change_node_app_config(deployment_dir, service_name, node_name, apps):
    panel = [app for app in apps if 'panel' in app.name][0]

    service_dir = os.path.join(deployment_dir, service_name)

    # create application's rel dir for current installation
    rel_dir = os.path.join(service_dir, node_name)
    if not os.path.isdir(rel_dir):
        os.makedirs(rel_dir, exist_ok=True)

    if panel.release_path:
        shutil.copy(os.path.join(panel.release_path, 'data/app.config'),
                    rel_dir)

    app_config_path = os.path.join(rel_dir, 'app.config')

    for app in apps:
        create_config_for_app(app, app_config_path)


def create_config_for_app(app, path):
    for attr, val in app.config.items():
        if 'panel' not in app.name:
            attr = '{}_{}'.format(app.name, attr)
        else:
            attr = 'onepanel_{}'.format(attr)
        replace(path, r'{{{}, .*}}'.format(attr), r'{{{}, "{}"}}'.format(attr, val))