"""
Module used for manipulating user config for one-env tool.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import os
import contextlib
from shutil import copyfile

from .. import terminal
from ..common import replace_in_file
from ..yaml_utils import load_yaml, dump_yaml
from . import get_one_env_directory, get_host_home


def update(key: str, val: str) -> None:
    user_cfg = load_yaml(get_user_config_path())
    user_cfg[key] = val
    dump_yaml(user_cfg, get_user_config_path())


def get_user_config_path() -> str:
    return os.path.join(get_one_env_directory(), 'config.yaml')


def exists() -> bool:
    return os.path.isfile(get_user_config_path())


def get_config_template_path() -> str:
    script_dir = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(script_dir, 'user_config_template.yaml')


def initialize() -> None:
    terminal.warning('This is the first run on this host. '
                     'Initializing config...')

    with contextlib.suppress(FileExistsError):
        os.mkdir(get_one_env_directory())
        terminal.info('Created directory: {}'
                      .format(get_one_env_directory()))

    user_cfg_path = get_user_config_path()
    if not os.path.isfile(user_cfg_path):
        copyfile(get_config_template_path(), user_cfg_path)
        terminal.info('Created config file: {}'.format(user_cfg_path))

        terminal.info('Initializing config: ')

        host_home_value = "'{}'".format(get_host_home())
        terminal.info('{key: >23}: {val: <0}'.format(key='hostHomeDir',
                                                     val=host_home_value))
        replace_in_file(user_cfg_path, '$hostHomeDir', host_home_value,
                        backup='.bak')

        terminal.info('{key: >23}: {val: <0}'.format(key='kubeHostHomeDir',
                                                     val=host_home_value))
        replace_in_file(user_cfg_path, '$kubeHostHomeDir', host_home_value,
                        backup='.bak')

        terminal.warning('Please make sure that the auto-generated '
                         'config is correct')


def ensure_exists() -> None:
    if not exists():
        initialize()


def get(key: str) -> str:
    config = load_yaml(get_user_config_path())
    return config[key]


def get_current_namespace() -> str:
    return get('currentNamespace')


def get_current_release_name() -> str:
    return get('currentHelmDeploymentName')
