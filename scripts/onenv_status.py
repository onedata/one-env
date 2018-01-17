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
    default=None,
    help='(optional) displays detailed status of given pod. The pod can be '
         'identified by any matching substring',
    dest='pod')

args = parser.parse_args()


def deployment_status():
    pods_list = pods.list_pods()
    print('ready: {}'.format(pods.are_all_pods_ready(pods_list)))
    print(' pods:')
    max_len = len(max(pods_list, key=len))
    for pod in pods_list:
        ready = 'Ready' if pods.is_pod_ready(pod) else 'Initializing'
        print('    {pod}    {readiness}'.format(pod=pod.rjust(max_len),
                                                readiness=ready))


def pod_status(pod):
    print('pod_status: ', pod)


if args.pod:
    matching_pods = pods.match_pods(args.pod)
    if len(matching_pods) == 0:
        console.error('There are no pods matching {}'.format(args.pod))
    elif len(matching_pods) == 1:
        pod_status(matching_pods[0])
    else:
        console.error('There is more than one matching pod:')
        for pod in matching_pods:
            print('    {}'.format(pod))
else:
    deployment_status()
