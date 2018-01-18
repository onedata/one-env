"""
Convenience functions for manipulating deployments via helm.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import cmd
import user_config


def GET_DEPLOYMENT(name): return ['helm', 'get', name]


def DELETE_DEPLOYMENT(name): return ['helm', 'delete', '--purge', name]


def deployment_name():
    return user_config.get('helmDeploymentName')


def deployment_exists():
    return 0 == cmd.check_return_code(GET_DEPLOYMENT(deployment_name()))


def clean_deployment():
    cmd.call(DELETE_DEPLOYMENT(deployment_name()))
