"""
Module used for persisting deployment data.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import os
# FIXME use config reader from readers
import yaml
import deployments_dir


# FIXME use config reader from readers
def load_yaml(path):
    with open(path) as f:
        return yaml.load(f)


# FIXME use config reader from readers
def write_yaml(data, path):
    with open(path, "w+") as f:
        yaml.safe_dump(data, f, default_flow_style=False)


def deployment_data_path():
    return os.path.join(deployments_dir.current_deployment_dir(),
                        'deployment_data.yml')


def get():
    if os.path.isfile(deployment_data_path()):
        return load_yaml(deployment_data_path())
    else:
        return {}


def put(dict):
    yaml = get()
    overwritten = {**yaml, **dict}
    write_yaml(overwritten, deployment_data_path())
