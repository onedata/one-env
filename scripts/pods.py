"""
Convenience functions for manipulating pods via kubectl.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import urllib3
from kubernetes import client, config
import re
import signal
import time

import cmd
import console
import sources
import user_config
from names_and_paths import *

SIGINT = 128 + int(signal.SIGINT)


def cmd_delete_jobs():
    return ['kubectl', 'delete', 'jobs', '--all']


def cmd_delete_pods():
    return ['kubectl', 'delete', 'pod', '--all']


def cmd_exec(pod, command):
    if isinstance(command, list):
        return ['kubectl', 'exec', '-it', pod, '--'] + command
    else:
        return ['kubectl', 'exec', '-it', pod, '--', command]


def cmd_logs(pod, follow=False):
    if follow:
        return ['kubectl', 'logs', '-f', pod]
    else:
        return ['kubectl', 'logs', pod]


def cmd_desc_stateful_set():
    return ['kubectl', 'describe', 'statefulset']


def get_name(pod):
    return pod.metadata.name


def get_service_type(pod):
    # returns SERVICE_ONEZONE | SERVICE_ONEPROVIDER
    return pod.metadata.labels.get('onedata-service')


def get_env_variables(pod):
    return pod.spec.containers[0].env


def get_env_variable(pod, env_name):
    envs = get_env_variables(pod)
    for env in envs:
        if env.name == env_name:
            return env.value
    return None


def get_domain(pod):
    return get_env_variable(pod, 'SERVICE_DOMAIN')


def get_hostname(pod):
    return '{}.{}'.format(get_env_variable(pod, 'HOSTNAME'),
                          get_domain(pod))


def get_ip(pod):
    return pod.status.pod_ip


def is_job(pod):
    return pod.metadata.owner_references[0].kind == 'Job'


def is_pod(pod):
    return pod.metadata.owner_references[0].kind == 'StatefulSet'


def is_job_finished(pod):
    return pod.status.phase == 'Succeeded'


def is_pod_running(pod):
    return pod.status.phase == 'Running'


def list_pods_and_jobs():
    urllib3.disable_warnings()
    config.load_kube_config()
    kube = client.CoreV1Api()
    namespace = user_config.get('namespace')
    return kube.list_namespaced_pod(namespace).items


def list_jobs():
    return list(filter(lambda pod: is_job(pod), list_pods_and_jobs()))


def all_jobs_succeeded():
    for job in list_jobs():
        if is_job_finished(job):
            return False
    return True


def clean_jobs():
    cmd.call(cmd_delete_jobs())


def list_pods():
    return list(filter(lambda pod: is_pod(pod), list_pods_and_jobs()))


def print_pods(pods):
    for pod in pods:
        print('    {}'.format(get_name(pod)))


def clean_pods():
    cmd.call(cmd_delete_pods())


def attach(pod, app_type=APP_TYPE_WORKER):
    pod_name = get_name(pod)
    try:
        service = get_service_type(pod)
        app = service_and_app_type_to_app(service, app_type)
        start_script = sources.start_script_path(app, pod_name)
        cmd.call(cmd_exec(pod_name, [start_script, 'attach-direct']))
    except KeyError:
        console.error('Only pods hosting onezone or oneprovider are supported.')
        return


# @TODO currently, pod exec in kubernetes-client
# does not work correctly. Use kubectl for now.
def pod_exec(pod):
    pod_name = get_name(pod)
    cmd.call(cmd_exec(pod_name, 'bash'))


def describe_stateful_set():
    return cmd.check_output(cmd_desc_stateful_set())


def file_exists_in_pod(pod, path):
    return 0 == cmd.check_return_code(cmd_exec(pod, ['test', '-e', path]))


def logs_follow(pod, infinite=False):
    def handler(signum, _frame):
        if signum == signal.SIGINT:
            print('')
            console.warning("Interrupted, exiting")
            return

    pod_name = get_name(pod)
    signal.signal(signal.SIGINT, handler)
    dots_num = 1
    ready = is_pod_running(pod)
    print('> {}'.format(pod_name))
    while not ready:
        dots = '.' * dots_num + ' ' * (3 - dots_num)
        console.print_same_line(
            '  Waiting for the pod to be available' + dots)
        time.sleep(0.5)
        dots_num = dots_num + 1 if dots_num < 3 else 1
        if is_pod_running(pod):
            ready = True
            print('')
    console.horizontal_line()

    res = cmd.call(cmd_logs(pod_name, True))

    if res == SIGINT:
        console.warning("Interrupted, exiting")
        return
    if infinite:
        console.horizontal_line()
        logs_follow(pod, infinite=infinite)
    else:
        print('')
        console.info('Log stream ended.')


# @TODO currently, pod logs displaying in kubernetes-client
# does not work correctly. Use kubectl for now.
def pod_logs(pod, interactive=False, follow=False, infinite=False):
    pod_name = get_name(pod)
    if interactive:
        if follow:
            logs_follow(pod, infinite=infinite)
        else:
            cmd.call(cmd_logs(pod_name, False))
    else:
        return cmd.check_output(cmd_logs(pod_name))


def app_logs_follow(pod, log_file, infinite=False):
    def handler(signum, _frame):
        if signum == signal.SIGINT:
            print('')
            console.warning("Interrupted, exiting")
            return

    pod_name = get_name(pod)
    signal.signal(signal.SIGINT, handler)
    dots_num = 1
    file_exists = file_exists_in_pod(pod_name, log_file)
    print('> {}'.format(log_file))
    while not file_exists:
        dots = '.' * dots_num + ' ' * (3 - dots_num)
        console.print_same_line(
            '  Waiting for the log file to be available' + dots)
        time.sleep(0.5)
        dots_num = dots_num + 1 if dots_num < 3 else 1
        if file_exists_in_pod(pod_name, log_file):
            file_exists = True
            print('')
    console.horizontal_line()
    res = cmd.call(cmd_exec(pod_name, ['tail', '-n', '+1', '-f', log_file]))

    if res == SIGINT:
        console.warning("Interrupted, exiting")
        return
    if infinite:
        console.horizontal_line()
        app_logs_follow(pod, log_file, infinite=infinite)
    else:
        print('')
        console.info('Log stream ended.')


def app_logs(pod, app_type=APP_TYPE_WORKER, logfile='info.log',
             interactive=False,
             follow=False, infinite=False):
    try:
        pod_name = get_name(pod)
        service = get_service_type(pod)
        app = service_and_app_type_to_app(service, app_type)
        log_file = sources.logs_file(app, pod_name, logfile)
        if follow:
            app_logs_follow(pod, log_file, infinite=infinite)
        else:
            if not file_exists_in_pod(pod_name, log_file):
                console.warning('The log file does not exist. Is the '
                                'deployment ready?\n'
                                '    tried: {}'.format(log_file))
                return
            if interactive:
                print('> {}'.format(log_file))
                console.horizontal_line()
                cmd.call(cmd_exec(pod_name, ['cat', log_file]))
            else:
                return cmd.check_output(cmd_exec(pod_name, ['cat', log_file]))
    except KeyError:
        console.error('Only pods hosting onezone or oneprovider are supported.')
        return


def list_logfiles(pod, app_type=APP_TYPE_WORKER):
    pod_name = get_name(pod)
    try:
        service = get_service_type(pod)
        app = service_and_app_type_to_app(service, app_type)
        logs_dir = sources.logs_dir(app, pod_name)
        print(cmd.check_output(cmd_exec(pod_name, ['ls', logs_dir])))
    except KeyError:
        console.error('Only pods hosting onezone or oneprovider are supported.')
        return


def match_pods(substring):
    pods_list = list_pods()
    # Accept dashes as wildcard characters
    pattern = '.*{}.*'.format(substring.replace('-', '.*'))
    return list(filter(lambda pod: re.match(pattern, get_name(pod)), pods_list))


def print_pod_choosing_hint():
    print('')
    console.info('To choose a pod, provide its full name or any matching, '
                 'unambiguous string. You can use dashes ("{}") for a wildcard '
                 'character, e.g.: {} will match {}.'.format(
        console.green_str('-'),
        console.green_str('z-1'),
        console.green_str('dev-onezone-node-1-0')))


def match_pod_and_run(pod, fun, allow_multiple=False):
    if not pod:
        console.error('Please choose a pod:')
        print_pods(list_pods())
        print_pod_choosing_hint()
        return

    matching_pods = match_pods(pod)
    if len(matching_pods) == 0:
        pods = list_pods()
        if pods:
            console.error(
                'There are no pods matching \'{}\'. Choose one of:'.format(pod))
            print_pods(pods)
            print_pod_choosing_hint()
        else:
            console.error('There are no pods running')
        return

    elif len(matching_pods) == 1:
        fun(matching_pods[0])

    else:
        if allow_multiple:
            for pod in matching_pods:
                fun(pod, multiple=True)
        else:
            console.error('There is more than one matching pod:')
            print_pods(matching_pods)
            print_pod_choosing_hint()
            return
