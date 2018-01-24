#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import requests

ENV_CONFIG_FILE_SUFFIX = 'env.config'
OFFSET = 4


class Node(object):
    def __init__(self, name, apps, service_name, deployment_dir):
        self.name = name
        self.apps = apps

        file_name = 'overlay.config'

        with open(os.path.join(deployment_dir, service_name, file_name), 'w') as f:
            # TODO:
            offset = 0
            f.write('[\n')
            offset += OFFSET
            f.write(offset * ' ' + '{onepanel, [\n')
            offset += 4
            for app in self.apps[:-1]:
                write_line_to_config_file(app, f, offset)
            write_line_to_config_file(self.apps[-1], f, offset,
                                      last_app=True)
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
