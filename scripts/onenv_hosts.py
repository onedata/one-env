"""
Part of onenv tool that that adds entries in /etc/hosts for all nodes in
current deployment. It has to be run with sudo.
"""

__author__ = "Michał Borzęcki, Wojciech Geisler"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"


import yaml
import argparse

import argparse_utils
from onenv_status import deployment_status


SCRIPT_DESCRIPTION = ('Adds entries in /etc/hosts file for all nodes in '
                      'current deployment. This script has to be run with'
                      'sudo.')

parser = argparse.ArgumentParser(
    prog='onenv hosts',
    formatter_class=argparse_utils.ArgumentsHelpFormatter,
    description=SCRIPT_DESCRIPTION
)


HOSTS_LOCATION = '/etc/hosts'


def main():
    onenv_ip_map = {}
    new_hosts_content = ''

    status = yaml.load(deployment_status())

    for pod in status['pods'].values():
        domain = pod.get('domain')
        ip = pod.get('ip')
        hostname = pod.get('hostname')

        if domain and ip:
            onenv_ip_map[domain] = ip
        if hostname and ip:
            onenv_ip_map[hostname] = ip

    onenv_domains = onenv_ip_map.keys()

    with open(HOSTS_LOCATION) as hosts_file:
        hosts_entries = [entry for entry in hosts_file
                         if len(entry.split()) == 2 and entry[0] != '#']

        for hosts_entry in hosts_entries:
            domain = hosts_entry.split()[1]
            if domain not in onenv_domains:
                new_hosts_content += hosts_entry
            else:
                print('Removed hosts entry: {}'.format(hosts_entry.strip()))

    for onenv_domain in onenv_domains:
        new_hosts_entry = '{}\t{}'.format(onenv_ip_map[onenv_domain],
                                          onenv_domain)
        new_hosts_content += '{}\n'.format(new_hosts_entry)
        print('Added hosts entry: {}'.format(new_hosts_entry))

    with open(HOSTS_LOCATION, 'w') as new_host_file:
        new_host_file.write(new_hosts_content)


if __name__ == '__main__':
    main()
