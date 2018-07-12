"""
Part of onenv tool that allows to attach directly to erlang VM of chosen pod in
onedata deployment.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"


import argparse
import contextlib

import pods
import helm
import user_config
import argparse_utils
from names_and_paths import *


SCRIPT_DESCRIPTION = 'Attaches directly to erlang VM in chosen pod. By ' \
                     'default, will attach to worker console, unless other ' \
                     'choice is specified in argument.'

parser = argparse.ArgumentParser(
    prog='onenv attach',
    formatter_class=argparse_utils.ArgumentsHelpFormatter,
    description=SCRIPT_DESCRIPTION
)

parser.add_argument(
    type=str,
    nargs='?',
    action='store',
    help='pod name (or matching pattern, use "-" for wildcard)',
    dest='pod')


components_group = parser.add_mutually_exclusive_group()

components_group.add_argument(
    '-p', '--panel',
    action='store_const',
    help='attach to onepanel\'s console in given pod',
    const=APP_TYPE_PANEL,
    dest='app_type')

components_group.add_argument(
    '-c', '--cluster-manager',
    action='store_const',
    help='attach to cluster-manager\'s console in given pod',
    const=APP_TYPE_CLUSTER_MANAGER,
    dest='app_type')

components_group.add_argument(
    '-w', '--worker',
    action='store_const',
    help='attach to (op|oz)-worker console in given pod',
    const=APP_TYPE_WORKER,
    dest='app_type')


def main():
    args = parser.parse_args()
    app_type = args.app_type
    if not app_type:
        app_type = APP_TYPE_WORKER

    user_config.ensure_exists()
    helm.ensure_deployment(exists=True, fail_with_error=True)

    if 'pod' not in args:
        args.pod = None

    with contextlib.suppress(KeyboardInterrupt):
        pods.match_pod_and_run(args.pod, lambda pod: pods.attach(pod, app_type))


if __name__ == '__main__':
    main()
