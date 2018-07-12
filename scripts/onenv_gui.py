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

import pods
import helm
import user_config
import console
import argparse_utils

SCRIPT_DESCRIPTION = 'Opens the GUI hosted by the service on given pod in ' \
                     'your default browser (uses the `open` command ' \
                     'underneath). By default, opens the oneprovider or ' \
                     'onezone GUI, unless the `panel` option is specified in ' \
                     'arguments.'

parser = argparse.ArgumentParser(
    prog='onenv open',
    formatter_class=argparse_utils.ArgumentsHelpFormatter,
    description=SCRIPT_DESCRIPTION
)

parser.add_argument(
    type=str,
    nargs='?',
    action='store',
    help='pod name (or matching pattern, use "-" for wildcard)',
    dest='pod')

parser.add_argument(
    '-p', '--panel',
    action='store_true',
    help='open the GUI of onepanel',
    dest='panel')

parser.add_argument(
    '-i', '--ip',
    action='store_true',
    help='use pod\'s IP rather than domain - useful when kubernetes domains '
         'cannot be resolved from the host.',
    dest='ip')

parser.add_argument(
    '-x', '--clipboard',
    action='store_true',
    help='copy the URL to clipboard and do not open it',
    dest='clipboard')


def main():
    args = parser.parse_args()

    user_config.ensure_exists()
    helm.ensure_deployment(exists=True, fail_with_error=True)

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
            url = 'https://{}:{}'.format(hostname, port)
            if 'clipboard' in args:
                pyperclip.copy(url)
                console.info('URL copied to clipboard ({})'.format(url))
            else:
                webbrowser.open(url)

    pods.match_pod_and_run(args.pod, open_fun)


if __name__ == '__main__':
    main()