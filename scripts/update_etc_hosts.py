#!/usr/bin/env python3

"""
Script that adds entries in /etc/hosts for all nodes in current deployment. It
has to be run with sudo.
"""

from subprocess import check_output
import yaml
import re


def update_etc_hosts(cwd='.'):
    re_node = re.compile(r'dev-.*')
    # TODO: make deployment status usable as function
    status = check_output(['./onenv', 'status'], cwd=cwd)
    status_object = yaml.load(status)

    with open('/etc/hosts') as etc_hosts:
        hosts_content = etc_hosts.readlines()

    pods = status_object['pods']
    for pod_name in pods:
        if re_node.match(pod_name):
            pod = pods.get(pod_name)
            domain = pod.get('domain')
            ip = pod.get('ip')
            if ip and domain:
                domain_entry = '{ip}\t{domain}\n'.format(ip=ip, domain=domain)
                try:
                    index = [i for i, x in enumerate(hosts_content)
                             if re.search(domain, x)][0]
                    hosts_content[index] = domain_entry
                except IndexError:
                    hosts_content.append(domain_entry)

    new_content = ''.join(hosts_content)

    with open('/etc/hosts', 'w+') as etc_hosts:
        etc_hosts.write(new_content)


def main():
    update_etc_hosts()


if __name__ == "__main__":
    main()
