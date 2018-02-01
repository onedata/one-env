import os
import textwrap


def create_node_config_file(deployment_dir, service_name, node_name, apps):
    with open(os.path.join(deployment_dir, service_name,
                           '{}-overlay.config'.format(node_name)), 'w') as f:
        apps_configs = []

        for app in apps:
            apps_configs.append(create_config_for_app(app))

        last_comma = apps_configs[-1].rfind(',')
        apps_configs[-1] = (apps_configs[-1][:last_comma] +
                            apps_configs[-1][last_comma + 1:])

        f.write('''
[
    {{onepanel, [
{}
    ]}}
].
'''.format(textwrap.indent('\n\n'.join(apps_configs), '        ')))


def create_config_for_app(app):
    app_config = []

    for attr, val in app.config.items():
        if 'panel' not in app.name:
            attr = '{}_{}'.format(app.name, attr)
        app_config.append('{{{0}, "{1}"}},'.format(attr, val))

    return '\n'.join(app_config)
