"""
Convenience functions for manipulating pods via kubectl.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import cmd
import console
import yaml
import sys
import binaries
import deployments_dir
import env_config
from config import readers

LIST_PODS = ['kubectl', 'get', 'pods', '-o', 'go-template', '--template',
             '{{range .items}}{{.metadata.name}}{{"\\n"}}{{end}}']


DELETE_JOBS = ['kubectl', 'delete', 'jobs', '--all']


def POD_READY(pod): return ['kubectl', 'get', 'pod', pod]


def EXEC(pod, command):
    if isinstance(command, list):
        return ['kubectl', 'exec', '-it', pod] + command
    else:
        return ['kubectl', 'exec', '-it', pod, command]


def LOGS(pod, follow=False):
    if follow:
        return ['kubectl', 'logs', '-f', pod]
    else:
        return ['kubectl', 'logs', pod]


def GET_POD(pod): return ['kubectl', 'get', 'pod', pod, '-o', 'yaml']


DESCRIBE_STATEFUL_SET = ['kubectl', 'describe', 'statefulset']


def is_pod_ready(pod):
    status = cmd.check_output(POD_READY(pod))
    # The above returns a string like this:
    #   NAME                      READY     STATUS    RESTARTS   AGE
    #   develop-onezone-node1-0   1/1       Running   0          1h
    # need to parse out the READY field
    pod_status = status.split('\n')[1]
    readiness = pod_status.split()[1]
    [ready, expected] = readiness.split('/')
    return ready == expected


def get_chart(pod):
    output = yaml.load(cmd.check_output(GET_POD(pod)))
    return output['metadata']['labels']['chart']


def chart_and_app_type_to_app(chart, app_type):
    return {
        ('onezone', 'worker'): 'oz-worker',
        ('onezone', 'panel'): 'oz-panel',
        ('onezone', 'cluster-manager'): 'cluster-manager',
        ('oneprovider', 'worker'): 'op-worker',
        ('oneprovider', 'panel'): 'op-panel',
        ('oneprovider', 'cluster-manager'): 'cluster-manager'
    }[(chart, app_type)]


def list_pods():
    output = cmd.check_output(LIST_PODS)
    lines = output.split('\n')
    return lines


def print_pods(pods):
    for pod in pods:
        print('    {}'.format(pod))


def describe_stateful_set():
    return cmd.check_output(DESCRIBE_STATEFUL_SET)



def are_all_pods_ready(pods):
    for pod in pods:
        if not is_pod_ready(pod):
            return False
    return True


def get_hostname(pod):
    return cmd.check_output(EXEC(pod, ['--', 'hostname', '-f']))


def get_ip(pod):
    return cmd.check_output(EXEC(pod, ['--', 'hostname', '-i']))


def exec(pod):
    cmd.call(EXEC(pod, 'bash'))


def logs(pod, interactive=False, follow=False):
    if interactive:
        cmd.call(LOGS(pod, follow))
    else:
        return cmd.check_output(LOGS(pod))


# app is one of: worker | panel | cluster-manager
def attach(pod, app_type='worker'):
    chart = get_chart(pod)
    current_deployment = deployments_dir.current_deployment_dir()
    env_cfg = readers.YamlConfigReader(
        env_config.config_path(current_deployment)).load()
    try:
        app = chart_and_app_type_to_app(chart, app_type)
        command = [binaries.start_script_path(app, env_cfg['binaries']),
               'attach-direct']
        cmd.call(EXEC(pod, command))
    except KeyError:
        console.error('Only pods hosting onezone or oneprovider are supported.')
        sys.exit(1)


def clean_jobs():
    cmd.call(DELETE_JOBS)


def match_pods(substring):
    pods_list = list_pods()
    return list(filter(lambda pod: substring in pod, pods_list))


def match_pod_and_run(pod, fun, allow_multiple=False):
    if not pod:
        console.error('Please choose a pod:')
        print_pods(list_pods())
        sys.exit(1)

    matching_pods = match_pods(pod)
    if len(matching_pods) == 0:
        console.error(
            'There are no pods matching \'{}\'. Choose one of:'.format(pod))
        print_pods(list_pods())
        sys.exit(1)

    elif len(matching_pods) == 1:
        fun(matching_pods[0])

    else:
        if allow_multiple:
            for pod in matching_pods:
                fun(pod, multiple=True)
        else:
            console.error('There is more than one matching pod:')
            print_pods(matching_pods)
            sys.exit(1)
