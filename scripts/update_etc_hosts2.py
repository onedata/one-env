#!/usr/bin/env python3
# coding=utf-8
# @author: Michał Borzęcki
# @author: Wojciech GEisler

import os
import yaml

hosts_location = '/etc/hosts'

onenv_ip_map = dict()
new_hosts_content = ''
origin_username = os.environ['SUDO_USER'] if 'SUDO_USER' in os.environ else os.environ['USER']

with os.popen('sudo -u ' + origin_username  + ' onenv status') as onenv_status:
    status = yaml.load(onenv_status)

    for pod in status['pods'].values():
        if pod['service-type'] in ['onezone', 'oneprovider']:
            domain = pod['domain']
            hostname = pod['hostname']
            ip = pod['ip']
            if domain and ip:
                onenv_ip_map[domain] = ip
            if hostname and ip:
                onenv_ip_map[hostname] = ip

onenv_domains = onenv_ip_map.keys()

with open(hosts_location) as hosts_file:
    hosts_entries = [entry for entry in hosts_file if len(entry.split()) == 2 and entry[0] != '#']

    for hosts_entry in hosts_entries:
        domain = hosts_entry.split()[1]
        if domain not in onenv_domains:
            new_hosts_content += hosts_entry
        else:
            print('Removed hosts entry: ' + hosts_entry.strip())

for onenv_domain in onenv_domains:
    new_hosts_entry = onenv_ip_map[onenv_domain] + '\t' + onenv_domain
    new_hosts_content += new_hosts_entry + '\n'
    print('Added hosts entry: ' + new_hosts_entry)

with open(hosts_location, 'w') as new_host_file:
    new_host_file.write(new_hosts_content)
