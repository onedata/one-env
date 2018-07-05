import os
import shutil


def default_config(name):
    env_file_arg = {
        'env_file': "/usr/lib/{}/lib/env.sh".format(name)
    }

    files_args = {
        'vm_args_file': "/etc/{}/vm.args".format(name),
        'app_config_file': "/var/lib/{}/app.config".format(name),
        'generated_config_file': "/etc/{}/autogenerated.config".format(name),
        'overlay_config_file': "/etc/{}/overlay.config".format(name)
    }

    web_args = {
        'web_key_file': "/etc/{0}/certs/web_key.pem".format(name),
        'web_cert_file': "/etc/{0}/certs/web_cert.pem".format(name),
        'cacerts_dir': "/etc/{0}/cacerts/".format(name)
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

    apps = {
        'cluster_manager': {**env_file_arg, **files_args, **cmds},
        'oz_worker': {**web_args, **files_args, **cmds},
        'op_worker': {**web_args, **files_args, **protocol_args, **cmds},
        'oz_panel': {**cmds, **files_args},
        'op_panel': {**cmds, **files_args}
    }
    return apps.get(name, dict())


class Application(object):
    def __init__(self, name: str, node_name: str, project_path: str,
                 additional_args, service,
                 service_dir, host_home_dir: str):
        self.name = name.replace('-', '_')

        if not project_path:
            self.config = default_config(self.name)
            return

        self.project_path = os.path.join(host_home_dir, project_path)

        release_path = '_build/default/rel/{}'.format(self.name)
        self.release_path = os.path.join(self.project_path, release_path)

        self.config = dict()

        release_args_paths = {
            'vm_args_file': 'etc/vm.args',
            'app_config_file': 'data/app.config',
            'generated_config_file': 'etc/autogenerated.config',
            'overlay_config_file': 'etc/overlay.config',
            'env_file': 'lib/env.sh',
            'web_key_file': 'etc/certs/web_key.pem',
            'web_cert_file': 'etc/certs/web_cert.pem',
            'cacerts_dir': 'etc/cacerts/',
            'protocol_key_file': 'etc/certs/protocol_key.pem',
            'protocol_cert_file': 'etc/certs/protocol_cert.pem',
            'start_cmd': 'bin/{} start'.format(self.name),
            'stop_cmd': 'bin/{} stop'.format(self.name),
            'status_cmd': 'bin/{} ping'.format(self.name)
        }

        for arg in default_config(self.name):
            if arg in release_args_paths:
                self.config[arg] = os.path.join(self.release_path,
                                                release_args_paths[arg])
            elif additional_args and arg in additional_args:
                self.config[arg] = additional_args[arg]
