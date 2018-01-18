"""
Part of onenv tool that displays the status of current onedata deployment.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import argparse
import pods
import console

SCRIPT_DESCRIPTION = 'Displays the status of current onedata deployment.'

parser = argparse.ArgumentParser(
    prog='onenv status',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    description=SCRIPT_DESCRIPTION
)

parser.add_argument(
    type=str,
    nargs='?',
    action='store',
    default=argparse.SUPPRESS,
    help='pod name (or any matching, unambiguous substring) - '
         'display detailed status of given pod.',
    dest='pod')

parser.add_argument(
    '-i', '--ip',
    action='store_true',
    default=argparse.SUPPRESS,
    help='display only pod\'s IP (pod must be specified)',
    dest='ip')

parser.add_argument(
    '-hn', '--hostname',
    action='store_true',
    default=argparse.SUPPRESS,
    help='display only pod\'s hostname (pod must be specified)',
    dest='hostname')

args = parser.parse_args()
if 'pod' not in args:
    args.pod = None


def deployment_status():
    pods_list = pods.list_pods()
    print('ready: {}'.format(pods.are_all_pods_ready(pods_list)))
    print('pods:')
    for pod in pods_list:
        pod_status(pod, multiple=True, indent='    ')


def pod_status(pod, multiple=False, indent=''):
    if multiple:
        print('{}{}:'.format(indent, pod))
        indent = indent + '    '

    if not multiple:
        print('{}name: {}'.format(indent, pod))
    print('{}ready: {}'.format(indent, pods.is_pod_ready(pod)))
    print('{}hostname: {}'.format(indent, pods.get_hostname(pod)))
    print('{}ip: {}'.format(indent, pods.get_ip(pod)))


def pod_ip(pod, multiple=False):
    ip = pods.get_ip(pod)
    if multiple:
        print('{}: {}'.format(pod, ip))
    else:
        print(ip)


def pod_hostname(pod, multiple=False):
    hostname = pods.get_hostname(pod)
    if multiple:
        print('{}: {}'.format(pod, hostname))
    else:
        print(hostname)


if args.pod:
    if 'ip' in args:
        fun = pod_ip
    elif 'hostname' in args:
        fun = pod_hostname
    else:
        fun = pod_status
    pods.match_pod_and_run(args.pod, fun, allow_multiple=True)
else:
    deployment_status()
