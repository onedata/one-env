"""
Part of onenv tool that displays the status of current onedata deployment.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import argparse
# import pyperclip
from io import StringIO
import sys
import pods
import config_maps
import helm
import console
import user_config
import argparse_utils
from kubernetes_utils import get_chart_name

SCRIPT_DESCRIPTION = 'Displays the status of current onedata deployment.'

parser = argparse.ArgumentParser(
    prog='onenv status',
    formatter_class=argparse_utils.ArgumentsHelpFormatter,
    description=SCRIPT_DESCRIPTION
)

parser.add_argument(
    type=str,
    nargs='?',
    action='store',
    help='pod name (or matching pattern, use "-" for wildcard) - '
         'display detailed status of given pod.',
    dest='pod')

parser.add_argument(
    '-i', '--ip',
    action='store_true',
    help='display only pod\'s IP',
    dest='ip')

parser.add_argument(
    '-hn', '--hostname',
    action='store_true',
    help='display only pod\'s hostname',
    dest='hostname')

parser.add_argument(
    '-d', '--domain',
    action='store_true',
    help='display only pod\'s domain',
    dest='domain')

parser.add_argument(
    '-x', '--clipboard',
    action='store_true',
    help='copy the output to clipboard',
    dest='clipboard')

args = parser.parse_args()

user_config.ensure_exists()
helm.ensure_deployment(exists=True, fail_with_error=False)


def deployment_status():
    component_list = pods.list_components()
    print('ready: {}'.format(pods.all_jobs_succeeded()))
    print('pods:')
    for component in component_list:
        config_map_name = pods.get_service_config_map(component)

        if config_map_name:
            config_map = config_maps.match_config_map(config_map_name)
            service_status(component, config_map, multiple=True, indent='    ')


def service_status(pod, config_map, multiple=False, indent=''):
    if multiple:
        print('{}{}:'.format(indent, pods.get_name(pod)))
        indent = indent + '    '
    else:
        print('{}name: {}'.format(indent, pods.get_name(pod)))

    if not config_maps.get_service_name(config_map):
        print('{}service-type: {}'.format(indent, pods.get_service_type(pod)),
              '{}ip: {}'.format(indent, pods.get_ip(pod)),
              '{}container_id: {}'.format(indent, pods.get_container_id(pod)),
              sep='\n')
    else:
        print('{}name: {}'.format(indent, config_maps.get_service_name(config_map)),
              '{}service-type: {}'.format(indent, pods.get_service_type(pod)),
              '{}domain: {}'.format(indent, config_maps.get_domain(config_map)),
              '{}hostname: {}.{}'.format(indent, pods.get_hostname(pod),
                                         config_maps.get_domain(config_map)),
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
    string_stdout = None
    if args.clipboard:
        sys.stdout = string_stdout = StringIO()

    if args.ip:
        pod = args.pod if args.pod else '-'
        pods.match_pod_and_run(pod, pod_ip, allow_multiple=True)
    elif args.hostname:
        pod = args.pod if args.pod else '-'
        pods.match_pod_and_run(pod, pod_hostname, allow_multiple=True)
    elif args.domain:
        pod = args.pod if args.pod else '-'
        pods.match_pod_and_run(pod, pod_domain, allow_multiple=True)
    else:
        if args.pod:
            pods.match_pod_and_run(args.pod, service_status, allow_multiple=True)
        else:
            deployment_status()

    if args.clipboard:
        sys.stdout = sys.__stdout__
        output = string_stdout.getvalue()
        # pyperclip.copy(output)
        output_sample = output.rstrip()
        if '\n' in output_sample:
            output_sample = '<multiline>'
        console.info('Output copied to clipboard ({})'.format(output_sample))


if __name__ == "__main__":
    main()
