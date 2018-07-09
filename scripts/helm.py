"""
Convenience functions for manipulating deployments via helm.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import sys
import cmd
import user_config
import console


def cmd_install(chart_path: str, values_paths: list):
    helm_install_cmd = ['helm', 'install', chart_path, '--namespace',
                        user_config.get_current_namespace(),
                        '--name', user_config.get_current_release_name()]

    for values_path in values_paths:
        helm_install_cmd.extend(['-f', values_path])
    return helm_install_cmd


def GET_DEPLOYMENT(name):
    return ['helm', 'get', name]


def DELETE_DEPLOYMENT(name):
    return ['helm', 'delete', '--purge', name]


def deployment_name():
    return user_config.get('currentHelmDeploymentName')


def deployment_exists():
    return 0 == cmd.check_return_code(GET_DEPLOYMENT(deployment_name()))


def clean_deployment():
    cmd.call(DELETE_DEPLOYMENT(deployment_name()))


def ensure_deployment(exists=True, fail_with_error=False):
    if exists:
        log = 'There is no active deployment'
    else:
        log = 'There already is an active deployment'

    if exists is not deployment_exists():
        if fail_with_error:
            console.error(log)
            sys.exit(1)
        else:
            console.info(log)
            sys.exit(0)

