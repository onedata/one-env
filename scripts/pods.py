"""
Convenience functions for manipulating pods via kubectl.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"


import re
import signal
import time
import sys


from kubernetes_utils import get_name, get_kube_client
import cmd
import console
import sources
import user_config
from names_and_paths import *
import helm
import subprocess


SIGINT = 128 + int(signal.SIGINT)


def cmd_delete_jobs():
    return ['kubectl', '--namespace', user_config.get_current_namespace(),
            'delete', 'jobs', '--all']


def cmd_delete_pods():
    return ['kubectl', '--namespace', user_config.get_current_namespace(),
            'delete', 'pod', '--all']


def cmd_exec(pod, command):
    if isinstance(command, list):
        return ['kubectl', '--namespace', user_config.get_current_namespace(),
                'exec', '-it', pod, '--'] + command
    else:
        return ['kubectl', '--namespace', user_config.get_current_namespace(),
                'exec', '-it', pod, '--', command]


def cmd_logs(pod, follow=False):
    if follow:
        return ['kubectl', '--namespace', user_config.get_current_namespace(),
                'logs', '-f', pod]
    else:
        return ['kubectl', '--namespace', user_config.get_current_namespace(),
                'logs', pod]


def cmd_desc_stateful_set():
    return ['kubectl', '--namespace', user_config.get_current_namespace(),
            'describe', 'statefulset']


def cmd_copy_to_pod(source_path, destination):
    pod_name, parsed_source_path = source_path.split(':')
    return ['kubectl', '--namespace', user_config.get_current_namespace(), 'cp',
            parsed_source_path, '{}:{}'.format(pod_name, destination)]


def cmd_copy_from_pod(source_path, destination):
    pod_name, parsed_source_path = source_path.split(':')
    return ['kubectl', '--namespace', user_config.get_current_namespace(), 'cp',
            '{}:{}'.format(pod_name, parsed_source_path), destination]


def cmd_rsync(source_path, destination_path):
    namespace = user_config.get_current_namespace()

    if ':' in source_path:
        pod_name, parsed_source_path = source_path.split(':')
        console.info('Rsyncing from pod {}: {} -> {} '.format(pod_name,
                                                              parsed_source_path,
                                                              destination_path))
        if namespace:
            rsh = 'kubectl --namespace {} exec {} -i -- '.format(namespace,
                                                                 pod_name)
        else:
            rsh = 'kubectl exec {} -i -- '.format(pod_name)

        rsync_cmd = ['rsync --info=progress2 -a --rsync-path={} --blocking-io '
                     '--rsh=\'{}\' rsync:. {}'.format(parsed_source_path, rsh,
                                                      destination_path)]
        return rsync_cmd
    else:
        pod_name, parsed_destination_path = destination_path.split(':')
        console.info('Rsyncing to pod {}: {} -> {} '.format(pod_name,
                                                            source_path,
                                                            parsed_destination_path))
        if namespace:
            rsh = 'kubectl --namespace {} exec {} -i -- '.format(namespace,
                                                                 pod_name)
        else:
            rsh = 'kubectl exec {} -i -- '.format(pod_name)
        rsync_cmd = ['rsync --info=progress2 -a --rsync-path={} --blocking-io '
                     '--rsh=\'{}\' {} rsync:.'.format(parsed_destination_path,
                                                      rsh, source_path)]
        return rsync_cmd


def get_client_provider_host(pod):
    return get_env_variable(pod, 'ONECLIENT_PROVIDER_HOST')


def get_node_num(pod_name: str):
    return pod_name.split('-')[-1]


def get_service_type(pod):
    # returns SERVICE_ONEZONE | SERVICE_ONEPROVIDER
    return pod.metadata.labels.get('component')


def get_container_id(pod):
    container_id = pod.status.container_statuses[0].container_id
    try:
        container_id = container_id.split('/')[-1]
    except Exception:
        container_id = None
    return container_id


def get_env_variables(pod):
    return pod.spec.containers[0].env


def get_volumes(pod):
    return pod.spec.volumes


def get_env_variable(pod, env_name):
    envs = get_env_variables(pod)
    for env in envs:
        if env.name == env_name:
            return env.value
    return None


def get_service_config_map(pod):
    for volume in get_volumes(pod):
        if volume.config_map:
            return volume.config_map.name


def get_hostname(pod):
    return pod.spec.hostname


def get_chart_name(pod):
    return pod.metadata.labels.get('chart')


def get_ip(pod):
    return pod.status.pod_ip


def is_job(pod):
    if pod.metadata.owner_references:
        return pod.metadata.owner_references[0].kind == 'Job'


def is_pod(pod):
    if pod.metadata.owner_references:
        return pod.metadata.owner_references[0].kind != 'Job'


def is_job_finished(pod):
    return pod.status.phase == 'Succeeded'


def is_pod_running(pod):
    return pod.status.phase == 'Running'


def list_pods_and_jobs():
    kube = get_kube_client()
    namespace = user_config.get_current_namespace()
    return kube.list_namespaced_pod(namespace).items


def list_jobs():
    return list(filter(lambda pod: is_job(pod), list_pods_and_jobs()))


def all_jobs_succeeded():
    for job in list_jobs():
        if not is_job_finished(job):
            return False
    return True


def all_pods_running():
    for pod in list_pods():
        if not is_pod_running(pod):
            return False
    return True


def wait_for_pod_to_be_running(pod):
    pod_name = get_name(pod)
    pod_ready = is_pod_running(pod)

    while not pod_ready:
        time.sleep(1)
        pod = match_pods(pod_name)[0]
        pod_ready = is_pod_running(pod)


def clean_jobs():
    cmd.call(cmd_delete_jobs())


def is_component(pod):
    return bool(pod.metadata.labels.get('component'))


def list_components():
    return list(filter(lambda pod: is_component(pod),
                       list_pods_and_jobs()))


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
            sys.exit(0)

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
            sys.exit(0)

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
        print(pod_name)
        service = get_service_type(pod)
        print(service)
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
