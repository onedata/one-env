"""
Part of onenv tool that that adds entries in /etc/hosts for all nodes in
current deployment. It has to be run with sudo.
"""

__author__ = "Michał Borzęcki, Wojciech Geisler"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import os
import argparse

import yaml

from .utils import arg_help_formatter


HOSTS_LOCATION = '/etc/hosts'


def get_onenv_ip_map():
    origin_username = os.environ.get('SUDO_USER') or os.environ.get('USER')
    script_dir = os.path.dirname(os.path.realpath(__file__))
    onenv_path = os.path.join(script_dir, '../onenv')

    user_option = ('sudo  -u {}'.format(origin_username)
                   if origin_username
                   else '')
    onenv_status_cmd = '{} {} status'.format(user_option, onenv_path)

    with os.popen(onenv_status_cmd) as onenv_status:
        status = yaml.load(onenv_status)

    onenv_ip_map = {}
    for pod in status['pods'].values():
        domain = pod.get('domain')
        ip = pod.get('ip')
        hostname = pod.get('hostname')

        if domain and ip:
            onenv_ip_map[domain] = ip
        if hostname and ip:
            onenv_ip_map[hostname] = ip

    return onenv_ip_map


def update_etc_hosts() -> None:
    new_hosts_content = ''
    onenv_ip_map = get_onenv_ip_map()
    onenv_domains = onenv_ip_map.keys()

    with open(HOSTS_LOCATION) as hosts_file:
        for host_entry in hosts_file:
            try:
                domain = host_entry.split()[1]
            except IndexError:
                new_hosts_content += host_entry
            else:
                if domain not in onenv_domains:
                    new_hosts_content += host_entry
                else:
                    print('Removed hosts entry: {}'.format(host_entry.strip()))

    for onenv_domain in onenv_domains:
        new_hosts_entry = '{}\t{}'.format(onenv_ip_map[onenv_domain],
                                          onenv_domain)
        new_hosts_content += '{}\n'.format(new_hosts_entry)
        print('Added hosts entry: {}'.format(new_hosts_entry))

    with open(HOSTS_LOCATION, 'w') as new_host_file:
        new_host_file.write(new_hosts_content)


def main() -> None:
    hosts_args_parser = argparse.ArgumentParser(
        prog='onenv hosts',
        formatter_class=arg_help_formatter.ArgumentsHelpFormatter,
        description='Adds entries in /etc/hosts file for all nodes in '
                    'current deployment. This script has to be run with'
                    'sudo.'
    )

    hosts_args_parser.parse_args()
    update_etc_hosts()


if __name__ == '__main__':
    main()
