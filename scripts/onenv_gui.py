"""
Part of onenv tool that allows to open the website hosted by a service on
given pod.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import argparse
import webbrowser

import pyperclip
from kubernetes.client import V1Pod

from .utils import terminal, arg_help_formatter
from .utils.one_env_dir import user_config
from .utils.k8s import helm, pods, config_maps


def main() -> None:
    gui_args_parser = argparse.ArgumentParser(
        prog='onenv gui',
        formatter_class=arg_help_formatter.ArgumentsHelpFormatter,
        description='Opens the GUI hosted by the service on given pod in '
                    'your default browser (uses the `open` command '
                    'underneath). By default, opens the oneprovider or '
                    'onezone GUI, unless the `panel` option is specified in '
                    'arguments.'
    )

    gui_args_parser.add_argument(
        nargs='?',
        help='pod name (or matching pattern, use "-" for wildcard)',
        dest='pod'
    )

    gui_args_parser.add_argument(
        '-p', '--panel',
        action='store_const',
        const='9443',
        default='443',
        help='open the GUI of onepanel',
        dest='port'
    )

    gui_args_parser.add_argument(
        '-i', '--ip',
        action='store_true',
        help='use pod\'s IP rather than domain - useful when kubernetes '
             'domains cannot be resolved from the host.'
    )

    gui_args_parser.add_argument(
        '-x', '--clipboard',
        action='store_true',
        help='copy the URL to clipboard and do not open it'
    )

    gui_args = gui_args_parser.parse_args()

    user_config.ensure_exists()
    helm.ensure_deployment(exists=True, fail_with_error=True)

    def open_fun(pod: V1Pod) -> None:
        if gui_args.ip:
            hostname = pods.get_ip(pod)
        else:
            config_map_name = pods.get_service_config_map(pod)
            config_map = config_maps.match_config_map(config_map_name)
            hostname = config_maps.get_domain(config_map)

        if not hostname:
            terminal.error('The pod is not ready yet')
        else:
            url = 'https://{}:{}'.format(hostname, gui_args.port)
            if gui_args.clipboard:
                pyperclip.copy(url)
                terminal.info('URL copied to clipboard ({})'.format(url))
            else:
                webbrowser.open(url)

    pods.match_pod_and_run(gui_args.pod, open_fun)


if __name__ == '__main__':
    main()
