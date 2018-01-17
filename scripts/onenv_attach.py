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
import console

SCRIPT_DESCRIPTION = 'Attaches directly to erlang VM in chosen pod. By ' \
                     ' default, will attach to worker console, unless other' \
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
    default=None,
    help='Pod name (or any matching, unambiguous substring)',
    dest='pod')

parser.add_argument(
    '-p', '--panel',
    action='store_true',
    default=None,
    help='Attaches to onepanel\'s console in given pod',
    dest='panel')

parser.add_argument(
    '-c', '--cluster-manager',
    action='store_true',
    default=None,
    help='Attaches to cluster-manager\'s console in given pod',
    dest='cluster_manager')

args = parser.parse_args()

if args.panel and args.cluster_manager:
    console.error('-p and -c options cannot be used together')
else:
    app_type = 'worker'
    if args.panel:
        app_type = 'panel'
    elif args.cluster_manager:
        app_type = 'cluster-manager'

    def attach_fun(pod):
        pods.attach(pod, app_type)

    pods.match_pod_and_run(args.pod, attach_fun)
