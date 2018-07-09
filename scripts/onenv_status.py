"""
Part of onenv tool that displays the status of current onedata deployment.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import argparse
import pyperclip
from io import StringIO
import sys
import pods
import helm
import console
import user_config

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
    help='pod name (or matching pattern, use "-" for wildcard) - '
         'display detailed status of given pod.',
    dest='pod')

parser.add_argument(
    '-i', '--ip',
    action='store_true',
    default=argparse.SUPPRESS,
    help='display only pod\'s IP',
    dest='ip')

parser.add_argument(
    '-hn', '--hostname',
    action='store_true',
    default=argparse.SUPPRESS,
    help='display only pod\'s hostname',
    dest='hostname')

parser.add_argument(
    '-d', '--domain',
    action='store_true',
    default=argparse.SUPPRESS,
    help='display only pod\'s domain',
    dest='domain')

parser.add_argument(
    '-x', '--clipboard',
    action='store_true',
    default=argparse.SUPPRESS,
    help='copy the output to clipboard',
    dest='clipboard')

user_config.ensure_exists()
helm.ensure_deployment(exists=True, fail_with_error=False)

args = parser.parse_args()


def deployment_status():
    pods_list = pods.list_pods()
    print('ready: {}'.format(pods.all_jobs_succeeded()))
    print('pods:')
    for pod in pods_list:
        pod_status(pod, multiple=True, indent='    ')


def pod_status(pod, multiple=False, indent=''):
    if multiple:
        print('{}{}:'.format(indent, pods.get_name(pod)))
        indent = indent + '    '
    else:
        print('{}name: {}'.format(indent, pods.get_name(pod)))

    print('{}name: {}'.format(indent, pods.get_service_name(pod)),
          '{}service-type: {}'.format(indent, pods.get_service_type(pod)),
          '{}hostname: {}'.format(indent, pods.get_hostname(pod)),
          '{}domain: {}'.format(indent, pods.get_domain(pod)),
          '{}ip: {}'.format(indent, pods.get_ip(pod)),
          '{}container_id: {}'.format(indent, pods.get_container_id(pod)),
          sep='\n')


def pod_ip(pod, multiple=False):
    ip = pods.get_ip(pod)
    if multiple:
        print('{}: {}'.format(pods.get_name(pod), ip))
    else:
        print(ip)


def pod_hostname(pod, multiple=False):
    hostname = pods.get_hostname(pod)
    if multiple:
        print('{}: {}'.format(pods.get_name(pod), hostname))
    else:
        print(hostname)


def pod_domain(pod, multiple=False):
    domain = pods.get_domain(pod)
    if multiple:
        print('{}: {}'.format(pods.get_name(pod), domain))
    else:
        print(domain)


def main():
    if 'pod' not in args:
        args.pod = None

    string_stdout = None
    if 'clipboard' in args:
        sys.stdout = string_stdout = StringIO()

    if 'ip' in args:
        pod = args.pod if args.pod else '-'
        pods.match_pod_and_run(pod, pod_ip, allow_multiple=True)
    elif 'hostname' in args:
        pod = args.pod if args.pod else '-'
        pods.match_pod_and_run(pod, pod_hostname, allow_multiple=True)
    elif 'domain' in args:
        pod = args.pod if args.pod else '-'
        pods.match_pod_and_run(pod, pod_domain, allow_multiple=True)
    else:
        if args.pod:
            pods.match_pod_and_run(args.pod, pod_status, allow_multiple=True)
        else:
            deployment_status()

    if 'clipboard' in args:
        sys.stdout = sys.__stdout__
        output = string_stdout.getvalue()
        pyperclip.copy(output)
        output_sample = output.rstrip()
        if '\n' in output_sample:
            output_sample = '<multiline>'
        console.info('Output copied to clipboard ({})'.format(output_sample))


if __name__ == "__main__":
    main()



