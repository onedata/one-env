"""
Part of onenv tool that allows to attach directly to erlang VM of chosen pod in
onedata deployment.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import argparse
import pods
from names_and_paths import *
import helm
import console
import user_config

SCRIPT_DESCRIPTION = 'Attaches directly to erlang VM in chosen pod. By ' \
                     'default, will attach to worker console, unless other ' \
                     'choice is specified in argument.'

parser = argparse.ArgumentParser(
    prog='onenv attach',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    description=SCRIPT_DESCRIPTION
)

parser.add_argument(
    type=str,
    nargs='?',
    action='store',
    default=argparse.SUPPRESS,
    help='pod name (or matching pattern, use "-" for wildcard)',
    dest='pod')

parser.add_argument(
    '-p', '--panel',
    action='store_true',
    default=argparse.SUPPRESS,
    help='attach to onepanel\'s console in given pod',
    dest=APP_TYPE_PANEL)

parser.add_argument(
    '-c', '--cluster-manager',
    action='store_true',
    default=argparse.SUPPRESS,
    help='attach to cluster-manager\'s console in given pod',
    dest=APP_TYPE_CLUSTER_MANAGER)

parser.add_argument(
    '-w', '--worker',
    action='store_true',
    default=argparse.SUPPRESS,
    help='attach to (op|oz)-worker console in given pod',
    dest=APP_TYPE_WORKER)

user_config.ensure_exists()
helm.ensure_deployment(exists=True, fail_with_error=True)

args = parser.parse_args()
if 'pod' not in args:
    args.pod = None

if APP_TYPE_PANEL in args and APP_TYPE_CLUSTER_MANAGER in args:
    console.error('-p and -c options cannot be used together')
else:
    try:
        app_type = APP_TYPE_WORKER
        if APP_TYPE_PANEL in args:
            app_type = APP_TYPE_PANEL
        elif APP_TYPE_CLUSTER_MANAGER in args:
            app_type = APP_TYPE_CLUSTER_MANAGER
        elif APP_TYPE_WORKER in args:
            app_type = APP_TYPE_WORKER

        def attach_fun(pod):
            pods.attach(pod, app_type)

        pods.match_pod_and_run(args.pod, attach_fun)
    except KeyboardInterrupt:
        pass
