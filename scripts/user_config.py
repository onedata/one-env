"""
Module used for manipulating user config for one-env tool.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import os
from shutil import copyfile
import fileinput
import console
# FIXME use config reader from readers
import yaml


def host_home():
    return os.path.expanduser('~')


def one_env_directory():
    return os.path.join(host_home(), '.one-env')


def user_config_path():
    return os.path.join(one_env_directory(), 'config.yaml')


def exists():
    return os.path.isfile(user_config_path())


def config_template_path():
    script_dir = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(script_dir, 'config_template.yaml')


def replace_in_file(file, pattern, replace):
    with fileinput.FileInput(file, inplace=True, backup='.bak') as file:
        for line in file:
            print(line.replace(pattern, replace), end='')


def initialize():
    console.warning(
        'This is the first run on this host. Initializing config...')

    try:
        os.mkdir(one_env_directory())
        console.info('Created directory: {}'.format(one_env_directory()))
    except FileExistsError:
        pass

    if not os.path.isfile(user_config_path()):
        copyfile(config_template_path(), user_config_path())
        console.info(
            'Created config file: {}'.format(user_config_path()))

        console.info('Initializing config: ')

        console.info('{key: >23}: {val: <0}'.format(
            key='hostHomeDir',
            val=host_home()))
        replace_in_file(user_config_path(), '$hostHomeDir', host_home())

        console.info('{key: >23}: {val: <0}'.format(
            key='kubeHostHomeDir',
            val=host_home()))
        replace_in_file(user_config_path(), '$kubeHostHomeDir', host_home())

        console.warning(
            'Please make sure that the auto-generated config is correct')


# FIXME use config reader from readers
def load_yaml(path):
    with open(path) as f:
        return yaml.load(f)


def get(key):
    config = load_yaml(user_config_path())
    return config[key]
