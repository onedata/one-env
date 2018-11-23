"""
Part of onenv tool that displays the status of current onedata deployment.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import sys
import argparse
import contextlib
from io import StringIO
from typing import Optional, Callable

import pyperclip
from kubernetes.client import V1ConfigMap, V1Pod

from .utils.one_env_dir import user_config
from .utils import terminal, arg_help_formatter
from .utils.names_and_paths import SERVICE_ONEZONE, SERVICE_ONEPROVIDER
from .utils.k8s import helm, pods, config_maps


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

DEFAULT_PARAMS = ['service-type', 'ip', 'container-id']


def get_hostname(pod: V1Pod, config_map: V1ConfigMap) -> str:
    return '{}.{}'.format(pods.get_hostname(pod),
                          config_maps.get_domain(config_map))


MIXED_PARAM_MAPPING = {
    'hostname': get_hostname
}

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


def deployment_status() -> str:
    components = pods.list_components()
    status = 'ready: {}\n'.format(pods.all_jobs_succeeded())
    status += 'pods:\n'

    for component in components:
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


def service_status(pod: V1Pod, config_map: Optional[V1ConfigMap],
                   multiple: bool = False, indent: str = '') -> str:
    status = ''

    if multiple:
        status += '{}{}:\n'.format(indent, pods.get_name(pod))
        indent += '    '
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


def pod_ip(pod: V1Pod, multiple: bool = False) -> str:
    ip = pods.get_ip(pod)
    if multiple:
        return '{}: {}'.format(pods.get_name(pod), ip)
    return ip


def pod_hostname(pod: V1Pod, multiple: bool = False) -> str:
    hostname = pods.get_hostname(pod)
    if multiple:
        return '{}: {}'.format(pods.get_name(pod), hostname)
    return hostname


def pod_domain(pod: V1Pod, multiple: bool = False) -> str:
    service_type = pods.get_service_type(pod)

    if service_type not in (SERVICE_ONEZONE, SERVICE_ONEPROVIDER):
        if multiple:
            return '{}: not supported'.format(pods.get_name(pod))
        return ('Domain attribute is supported only for provider and '
                'zone pods')

    config_map_name = pods.get_service_config_map(pod)
    config_map = config_maps.match_config_map(config_map_name)
    domain = config_maps.get_domain(config_map)

    if multiple:
        return '{}: {}'.format(pods.get_name(pod), domain)
    return domain


def print_pods_info(pod_name: str, fun: Callable[[V1Pod, bool], str]) -> None:
    matching_pods = pods.match_pods(pod_name)
    for pod in matching_pods:
        print(fun(pod, True))


def main() -> None:
    status_args_parser = argparse.ArgumentParser(
        prog='onenv status',
        formatter_class=arg_help_formatter.ArgumentsHelpFormatter,
        description='Displays the status of current onedata deployment.'
    )

    status_args_parser.add_argument(
        nargs='?',
        help='pod name (or matching pattern, use "-" for wildcard) - '
             'display detailed status of given pod.',
        dest='pod'
    )

    status_args_parser.add_argument(
        '-x', '--clipboard',
        action='store_true',
        help='copy the output to clipboard'
    )

    info_type_group = status_args_parser.add_mutually_exclusive_group()

    info_type_group.add_argument(
        '-i', '--ip',
        action='store_const',
        help='display only pod\'s IP',
        const=pod_ip,
        dest='info_fun'
    )

    info_type_group.add_argument(
        '-n', '--hostname',
        action='store_const',
        help='display only pod\'s hostname',
        const=pod_hostname,
        dest='info_fun'
    )

    info_type_group.add_argument(
        '-d', '--domain',
        action='store_const',
        help='display only pod\'s domain',
        const=pod_domain,
        dest='info_fun'
    )

    status_args = status_args_parser.parse_args()
    user_config.ensure_exists()
    helm.ensure_deployment(exists=True, fail_with_error=False)

    if status_args.clipboard:
        string_stdout = StringIO()
    else:
        string_stdout = sys.stdout

    with contextlib.redirect_stdout(string_stdout):
        if status_args.info_fun:
            pod = status_args.pod or '-'
            print_pods_info(pod, status_args.info_fun)
        else:
            if status_args.pod:
                matching_pods = pods.match_pods(status_args.pod)
                for pod in matching_pods:
                    config_map_name = pods.get_service_config_map(pod)
                    if config_map_name:
                        config_map = config_maps.match_config_map(config_map_name)
                        print(service_status(pod, config_map, multiple=True))
            else:
                print(deployment_status())

    if status_args.clipboard:
        output = string_stdout.getvalue()
        pyperclip.copy(output)
        output_sample = output.rstrip()

        if '\n' in output_sample:
            output_sample = '<multiline>'
        terminal.info('Output copied to clipboard ({})'.format(output_sample))


if __name__ == '__main__':
    main()
