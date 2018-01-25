#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

OFFSET = 4


def create_node_config_file(deployment_dir, service_name, node_name, apps):
    with open(os.path.join(deployment_dir, service_name,
                           '{}-overlay.config'.format(node_name)), 'w') as f:
        # TODO:
        offset = 0
        f.write('[\n')
        offset += OFFSET
        f.write(offset * ' ' + '{onepanel, [\n')
        offset += 4
        for app in apps[:-1]:
            write_line_to_config_file(app, f, offset)
        write_line_to_config_file(apps[-1], f, offset, last_app=True)
        offset -= 4
        f.write(offset * ' ' + ']}\n')
        offset -= 4
        f.write('].\n')


def write_line_to_config_file(app, file, offset, last_app=False):
    if not last_app:
        for attr, val in app.config.items():
            # TODO:
            if 'panel' not in app.name:
                attr = '{}_{}'.format(app.name, attr)
            file.write(offset * ' ' + '{{{0}, "{1}"}},\n'.format(attr, val))
        file.write('\n')
    else:
        for attr, val in list(app.config.items())[:-1]:
            # TODO:
            if 'panel' not in app.name:
                attr = '{}_{}'.format(app.name, attr)
            file.write(offset * ' ' + '{{{0}, "{1}"}},\n'.format(attr, val))

        attr, val = list(app.config.items())[-1]
        # TODO:
        if 'panel' not in app.name:
            attr = '{}_{}'.format(app.name, attr)
        file.write(offset * ' ' + '{{{0}, "{1}"}}\n'.format(attr, val))



