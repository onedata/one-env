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


def get_hostname(pod, config_map):
    return '{}.{}'.format(pods.get_hostname(pod),
                          config_maps.get_domain(config_map))


POD_PARAM_FUN_MAPPING = {
    'service-type': pods.get_service_type,
    'ip': pods.get_ip,
    'container-id':  pods.get_container_id,
    'provider-host': pods.get_client_provider_host
}
CONFIG_MAP_PARAM_FUN_MAPPING = {
    'name': config_maps.get_service_name,
    'domain': config_maps.get_domain
}
MIXED_PARAM_MAPPING = {
    'hostname': get_hostname
}
DEFAULT_PARAMS = ['service-type', 'ip', 'container-id']
SERVICES_PARAMS = {
    'onezone': (list(CONFIG_MAP_PARAM_FUN_MAPPING.keys()) +
                ['service-type', 'ip', 'container-id'] +
                list(MIXED_PARAM_MAPPING.keys())),
    'oneprovider': (list(CONFIG_MAP_PARAM_FUN_MAPPING.keys()) +
                    ['service-type', 'ip', 'container-id'] +
                    list(MIXED_PARAM_MAPPING.keys())),
    'oneclient': ['service-type', 'ip', 'container-id', 'provider-host'],
    'onedata-cli': DEFAULT_PARAMS,
    'luma': DEFAULT_PARAMS
}
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


def deployment_status():
    component_list = pods.list_components()
    status = 'ready: {}\n'.format(pods.all_jobs_succeeded())
    status += 'pods:\n'

    for component in component_list:
        config_map = None
        config_map_name = pods.get_service_config_map(component)

        if config_map_name:
            config_map = config_maps.match_config_map(config_map_name)

        service_type = pods.get_service_type(component)
        service_params = SERVICES_PARAMS.get(service_type, [])

        if service_params:
            status += service_status(component, config_map, multiple=True,
                                     indent='    ')

    return status


def service_status(pod, config_map=None, multiple=False, indent=''):
    status = ''

    if multiple:
        status += '{}{}:\n'.format(indent, pods.get_name(pod))
        indent = indent + '    '
    else:
        status += '{}name: {}\n'.format(indent, pods.get_name(pod))

    service_type = pods.get_service_type(pod)
    service_params = SERVICES_PARAMS.get(service_type, [])

    for param in service_params:
        if POD_PARAM_FUN_MAPPING.get(param):
            fun = POD_PARAM_FUN_MAPPING.get(param)
            status += '{}{}: {}\n'.format(indent, param, fun(pod))
        elif CONFIG_MAP_PARAM_FUN_MAPPING.get(param):
            fun = CONFIG_MAP_PARAM_FUN_MAPPING.get(param)
            status += '{}{}: {}\n'.format(indent, param, fun(config_map))
        else:
            fun = MIXED_PARAM_MAPPING.get(param)
            status += '{}{}: {}\n'.format(indent, param, fun(pod, config_map))
    return status


def pod_ip(pod, multiple=False):
    ip = pods.get_ip(pod)
    if multiple:
        return '{}: {}'.format(pods.get_name(pod), ip)
    else:
        return ip


def pod_hostname(pod, multiple=False):
    hostname = pods.get_hostname(pod)
    if multiple:
        return '{}: {}'.format(pods.get_name(pod), hostname)
    else:
        return hostname


def pod_domain(pod, multiple=False):
    service_type = pods.get_service_type(pod)

    if service_type not in ['onezone', 'oneprovider']:
        if multiple:
            return '{}: not supported'.format(pods.get_name(pod))
        else:
            print('Domain attribute is supported only for provider and zone '
                  'pods')

    config_map_name = pods.get_service_config_map(pod)
    config_map = config_maps.match_config_map(config_map_name)
    domain = config_maps.get_domain(config_map)

    if multiple:
        return '{}: {}'.format(pods.get_name(pod), domain)
    else:
        return domain


def print_pods_info(pod, fun):
    matching_pods = pods.match_pods(pod)
    for pod in matching_pods:
        print(fun(pod, multiple=True))


def main():
    args = parser.parse_args()
    user_config.ensure_exists()
    helm.ensure_deployment(exists=True, fail_with_error=False)

    string_stdout = None
    if args.clipboard:
        sys.stdout = string_stdout = StringIO()

    if args.ip:
        pod = args.pod if args.pod else '-'
        print_pods_info(pod, pod_ip)
    elif args.hostname:
        pod = args.pod if args.pod else '-'
        print_pods_info(pod, pod_hostname)
    elif args.domain:
        pod = args.pod if args.pod else '-'
        print_pods_info(pod, pod_domain)
    else:
        if args.pod:
            matching_pods = pods.match_pods(args.pod)
            for pod in matching_pods:
                config_map_name = pods.get_service_config_map(pod)
                if config_map_name:
                    config_map = config_maps.match_config_map(config_map_name)

                    print(service_status(pod, config_map, multiple=True))
        else:
            print(deployment_status())

    if args.clipboard:
        sys.stdout = sys.__stdout__
        output = string_stdout.getvalue()
        # pyperclip.copy(output)
        output_sample = output.rstrip()
        if '\n' in output_sample:
            output_sample = '<multiline>'
        console.info('Output copied to clipboard ({})'.format(output_sample))


if __name__ == '__main__':
    main()
