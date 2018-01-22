"""
Part of onenv tool that allows to open the website hosted by a service on
given pod.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import argparse
import cmd
import pods
import helm
import user_config
import console

SCRIPT_DESCRIPTION = 'Opens the GUI hosted by the service on given pod in ' \
                     'your default browser (uses the `open` command ' \
                     'underneath). By default, opens the oneprovider or ' \
                     'onezone GUI, unless the `panel` option is specified in ' \
                     'arguments.'

parser = argparse.ArgumentParser(
    prog='onenv open',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    description=SCRIPT_DESCRIPTION
)

parser.add_argument(
    type=str,
    nargs='?',
    action='store',
    default=argparse.SUPPRESS,
    help='pod name (or any matching, unambiguous substring)',
    dest='pod')

parser.add_argument(
    '-p', '--panel',
    action='store_true',
    default=argparse.SUPPRESS,
    help='open the GUI of onepanel',
    dest='panel')

parser.add_argument(
    '-i', '--ip',
    action='store_true',
    default=argparse.SUPPRESS,
    help='use pod\'s IP rather than domain - useful when kubernetes domains '
         'cannot be resolved from the host.',
    dest='ip')

user_config.ensure_exists()
helm.ensure_deployment(exists=True, fail_with_error=True)

args = parser.parse_args()
if 'pod' not in args:
    args.pod = None

port = 443
if 'panel' in args:
    port = 9443


def open_fun(pod):
    if 'ip' in args:
        hostname = pods.get_ip(pod)
    else:
        hostname = pods.get_domain(pod)

    if not hostname:
        console.error('The pod is not ready yet')
    else:
        cmd.call(['open', 'https://{}:{}'.format(hostname, port)])


pods.match_pod_and_run(args.pod, open_fun)
