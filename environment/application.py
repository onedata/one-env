#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil


def default_config(name):
    env_file_arg = {
        'env_file': "/usr/lib/{}/lib/env.sh".format(name)
    }

    files_args = {
        'vm_args_file': "/etc/{}/vm.args".format(name),
        'app_config_file': "/etc/{}/app.config".format(name)
    }

    web_args = {
        'web_key_file': "/etc/{0}/certs/web_key.pem".format(name),
        'web_cert_file': "/etc/{0}/certs/web_cert.pem".format(name)
    }

    protocol_args = {
        'protocol_key_file': "/etc/{}/certs/protocol_key.pem".format(name),
        'protocol_cert_file': "/etc/{}/certs/protocol_cert.pem".format(name)
    }

    cmds = {
        'start_cmd': "service {} start".format(name),
        'stop_cmd': "service {} stop".format(name),
        'status_cmd': "service {} ping".format(name)
    }

    test_web_cert_domain = {
        'test_web_cert_domain': 'onedata.org'
    }

    apps = {
        'cluster_manager': dict(env_file_arg.items() + files_args.items() +
                                cmds.items()),
        'oz_worker': dict(web_args.items() + files_args.items() +
                          cmds.items()),
        'op_worker': dict(web_args.items() + files_args.items() +
                          protocol_args.items() + cmds.items()),
        'oz_panel': dict(cmds.items() + files_args.items() + test_web_cert_domain.items()),
        'op_panel': dict(cmds.items() + files_args.items() + test_web_cert_domain.items())
    }
    return apps.get(name, dict())


class Application(object):
    def __init__(self, name, node_name, project_path, additional_args, service):
        self.name = name.replace('-', '_')

        if not project_path:
            self.config = default_config(self.name)
            return

        self.project_path = project_path

        release_path = '_build/default/rel/{}'.format(self.name)
        self.release_path = release_path if os.path.isabs(release_path) \
            else os.path.join(self.project_path, release_path)

        self.node_path = os.path.join('/root/bin/node', self.name)

        self.config = dict()

        release_args_paths = {
            'vm_args_file': 'etc/vm.args',
            'app_config_file': 'etc/app.config',
            'env_file': 'lib/env.sh',
            'web_key_file': 'etc/certs/web_key.pem',
            'web_cert_file': 'etc/certs/web_cert.pem',
            'protocol_key_file': 'etc/certs/protocol_key.pem',
            'protocol_cert_file': 'etc/certs/protocol_cert.pem',
            'start_cmd': 'bin/{} start'.format(self.name),
            'stop_cmd': 'bin/{} stop'.format(self.name),
            'status_cmd': 'bin/{} ping'.format(self.name)
        }

        # create tmp dir for project
        tmp_dir = os.path.join(self.project_path, 'tmp')
        if not os.path.exists(tmp_dir):
            os.mkdir(tmp_dir)

        # create rel dir for project
        rel_dir = os.path.join(self.project_path, 'tmp',
                               '{}-{}-{}-rel'.format(service, node_name, name))
        if os.path.exists(rel_dir):
            shutil.rmtree(rel_dir)
        shutil.copytree(self.release_path, rel_dir, symlinks=True)

        for arg in default_config(self.name):
            if arg in release_args_paths:
                self.config[arg] = os.path.join(self.release_path,
                                                release_args_paths[arg])
            elif additional_args and arg in additional_args:
                self.config[arg] = additional_args[arg]
