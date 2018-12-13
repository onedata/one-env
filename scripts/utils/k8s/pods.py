"""
Convenience functions for manipulating pods via kubectl.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import re
import sys
import time
import signal
import subprocess
from collections import defaultdict
from typing import List, Callable, Dict, Union, IO, Any, Optional

from kubernetes.client import V1Pod, V1EnvVar, V1Volume, V1PersistentVolume

from ..deployment import sources_paths
from ..one_env_dir import user_config
from .. import shell, terminal
from ..k8s.kubernetes_utils import get_name, get_kube_client
from ..names_and_paths import (APP_TYPE_WORKER, service_and_app_type_to_app,
                               service_name_to_alias_mapping)


SIGINT = 128 + int(signal.SIGINT)


def get_pods_cmd(pod_name: Optional[str] = None,
                 output: Optional[str] = None) -> List[str]:
    command = ['kubectl', '--namespace', user_config.get_current_namespace(),
               'get', 'pod']

    if output:
        command.extend(['-o', output])

    if pod_name:
        command.append(pod_name)

    return command


def describe_pods_cmd() -> List[str]:
    return ['kubectl', '--namespace', user_config.get_current_namespace(),
            'describe', 'pods']


def delete_kube_object_cmd(object_type, delete_all=True, label=None,
                           include_uninitialized=False):
    command = ['kubectl', '--namespace', user_config.get_current_namespace(),
               'delete', object_type]

    if delete_all:
        command.append('--all')

    if label:
        command.extend(['-l', label])

    if include_uninitialized:
        command.append('--include-uninitialized')

    return command


def exec_cmd(pod: str, command: Any, it: bool = False) -> List[str]:
    cmd = ['kubectl', '--namespace', user_config.get_current_namespace(),
           'exec']

    if it:
        cmd.append('-it')

    cmd.extend([pod, '--'])

    if isinstance(command, list):
        cmd += command
    else:
        cmd.append(command)
    return cmd


def logs_cmd(pod: str, follow: bool = False) -> List[str]:
    if follow:
        return ['kubectl', '--namespace', user_config.get_current_namespace(),
                'logs', '-f', pod]
    return ['kubectl', '--namespace', user_config.get_current_namespace(),
            'logs', pod]


def desc_stateful_set_cmd() -> List[str]:
    return ['kubectl', '--namespace', user_config.get_current_namespace(),
            'describe', 'statefulset']


def copy_to_pod_cmd(source_path: str, destination: str) -> List[str]:
    pod_name, parsed_source_path = source_path.split(':')
    return ['kubectl', '--namespace', user_config.get_current_namespace(), 'cp',
            parsed_source_path, '{}:{}'.format(pod_name, destination)]


def copy_from_pod_cmd(source_path: str, destination: str) -> List[str]:
    pod_name, parsed_source_path = source_path.split(':')
    return ['kubectl', '--namespace', user_config.get_current_namespace(), 'cp',
            '{}:{}'.format(pod_name, parsed_source_path), destination]


def rsync_cmd(source_path: str, destination_path: str,
              delete: Optional[bool] = None) -> List[str]:
    namespace = user_config.get_current_namespace()
    options = '--delete' if delete else ''
    cmd = ['rsync', '--info=progress2', '--archive', '--blocking-io']
    if options:
        cmd.append(options)

    if namespace:
        rsh_fmt = 'kubectl --namespace {} exec {{}} -i -- '.format(namespace)
    else:
        rsh_fmt = 'kubectl exec {} -i -- '

    if ':' in source_path:
        pod_name, pod_path = source_path.split(':')
        host_path = destination_path
        rsh = rsh_fmt.format(pod_name)
        cmd += ['--rsync-path={}'.format(pod_path), '--rsh={}'.format(rsh),
                'rsync:.', '{}'.format(host_path)]

        terminal.info('Rsyncing from pod {}: {} -> {} '
                      .format(pod_name, pod_path, host_path))
    else:
        pod_name, pod_path = destination_path.split(':')
        host_path = source_path
        rsh = rsh_fmt.format(pod_name)
        cmd += ['--rsync-path={}'.format(pod_path), '--rsh={}'.format(rsh),
                '{}'.format(host_path), 'rsync:.']

        terminal.info('Rsyncing to pod {}: {} -> {} '
                      .format(pod_name, host_path, pod_path))
    return cmd


def get_client_provider_host(pod: V1Pod) -> Optional[str]:
    return get_env_variable(pod, 'ONECLIENT_PROVIDER_HOST')


def get_node_num(pod_name: str) -> str:
    return pod_name.split('-')[-1]


def get_service_type(pod: V1Pod) -> Optional[str]:
    # returns SERVICE_ONEZONE | SERVICE_ONEPROVIDER
    return pod.metadata.labels.get('component')


def get_container_id(pod: V1Pod) -> Optional[str]:
    try:
        container_id = pod.status.container_statuses[0].container_id
        container_id = container_id.split('/')[-1]
    except KeyError:
        container_id = None
    return container_id


def get_env_variables(pod: V1Pod) -> List[V1EnvVar]:
    return pod.spec.containers[0].env


def get_volumes(pod: V1Pod) -> List[V1Volume]:
    return pod.spec.volumes


def get_env_variable(pod: V1Pod, env_name: str) -> Optional[str]:
    envs = get_env_variables(pod)
    for env in envs:
        if env.name == env_name:
            return env.value
    return None


def get_service_config_map(pod: V1Pod) -> Optional[str]:
    for volume in get_volumes(pod):
        if volume.config_map:
            return volume.config_map.name
    return None


def get_hostname(pod: V1Pod) -> Optional[str]:
    return pod.spec.hostname


def get_chart_name(pod: V1Pod) -> Optional[str]:
    return pod.metadata.labels.get('chart')


def get_ip(pod: V1Pod) -> Optional[str]:
    return pod.status.pod_ip


def is_job(pod: V1Pod) -> bool:
    if pod.metadata.owner_references:
        return pod.metadata.owner_references[0].kind == 'Job'
    return False


def is_pod(pod: V1Pod) -> bool:
    if pod.metadata.owner_references:
        return pod.metadata.owner_references[0].kind != 'Job'
    if pod.metadata.owner_references is None:
        return True
    return False


def has_job_finished(pod: V1Pod) -> bool:
    return pod.status.phase == 'Succeeded'


def is_pod_running(pod: V1Pod) -> bool:
    return pod.status.phase == 'Running'


def list_pvs() -> List[V1PersistentVolume]:
    kube = get_kube_client()
    return kube.list_persistent_volume().items


def list_pods_and_jobs() -> List[V1Pod]:
    kube = get_kube_client()
    namespace = user_config.get_current_namespace()
    return kube.list_namespaced_pod(namespace).items


def list_jobs() -> List[V1Pod]:
    return [pod for pod in list_pods_and_jobs() if is_job(pod)]


def all_jobs_succeeded() -> bool:
    return all(has_job_finished(job) for job in list_jobs())


def all_pods_running() -> bool:
    return all(is_pod_running(pod) for pod in list_pods())


def wait_for_pods_to_be_running(pod_substring: str, timeout: int = 60) -> None:
    start_time = time.time()
    pod_list = []

    while int(time.time() - start_time) <= timeout:
        pod_list = match_pods(pod_substring)
        if all(is_pod_running(pod) for pod in pod_list):
            return
        time.sleep(1)

    terminal.error('Timeout while waiting for the following pods to be '
                   'running:')

    for pod in pod_list:
        if not is_pod_running(pod):
            terminal.red_str('    ' + get_name(pod))


def clean_jobs() -> None:
    shell.call(delete_kube_object_cmd('job'))


def is_component(pod: V1Pod) -> bool:
    return bool(pod.metadata.labels.get('component'))


def list_components() -> List[V1Pod]:
    return [pod for pod in list_pods_and_jobs() if is_component(pod)]


def list_pods() -> List[V1Pod]:
    return [pod for pod in list_pods_and_jobs() if is_pod(pod)]


def print_pods(pods: List[V1Pod]) -> None:
    for pod in pods:
        print('    {}'.format(get_name(pod)))


def clean_pods() -> None:
    shell.call(delete_kube_object_cmd('pod'))


def attach(pod: V1Pod, app_type: str = APP_TYPE_WORKER) -> None:
    pod_name = get_name(pod)
    try:
        service = get_service_type(pod)
        app = service_and_app_type_to_app(service, app_type)
        start_script = sources_paths.get_start_script_path(app, pod_name)
        shell.call(exec_cmd(pod_name, [start_script, 'attach-direct'],
                            it=True))
    except KeyError:
        terminal.error('Only pods hosting onezone or oneprovider are '
                       'supported.')


def pod_exec(pod: V1Pod) -> None:
    pod_name = get_name(pod)
    shell.call(exec_cmd(pod_name, 'bash', it=True))


def describe_stateful_set() -> str:
    return shell.check_output(desc_stateful_set_cmd())


def file_exists_in_pod(pod: str, path: str) -> bool:
    ret = shell.check_return_code(exec_cmd(pod, ['test', '-e', path]))
    return ret == 0


def pod_logs(pod: V1Pod, interactive: bool = False, follow: bool = False,
             infinite: bool = False,
             stderr: Union[None, int, IO[Any]] = subprocess.DEVNULL) -> Optional[str]:
    pod_name = get_name(pod)
    if interactive:
        if follow:
            logs_follow(pod, infinite=infinite)
        else:
            shell.call(logs_cmd(pod_name, False))
        return None
    else:
        return shell.check_output(logs_cmd(pod_name), stderr)


def end_log(res, logs_follow_fun, *args, infinite=False) -> None:
    if res == SIGINT:
        terminal.warning("Interrupted, exiting")
        return
    if infinite:
        terminal.horizontal_line()
        logs_follow_fun(args, infinite=infinite)
    else:
        print('')
        terminal.info('Log stream ended.')


def logs(condition, *args):
    def handler(signum, _frame):
        if signum == signal.SIGINT:
            print('')
            terminal.warning('Interrupted, exiting')
            sys.exit(0)
    signal.signal(signal.SIGINT, handler)
    dots_num = 1
    condition_satisfied = condition(*args)
    while not condition_satisfied:
        dots = '.' * dots_num + ' ' * (3 - dots_num)
        terminal.print_same_line('  Waiting for the pod to be available'
                                 + dots)
        time.sleep(0.5)
        dots_num = dots_num + 1 if dots_num < 3 else 1
        if condition(*args):
            condition_satisfied = True
            print('')
    terminal.horizontal_line()


def logs_follow(pod: V1Pod, infinite: bool = False) -> None:
    pod_name = get_name(pod)
    logs(is_pod_running, pod)
    res = shell.call(logs_cmd(pod_name, True))
    end_log(res, logs_follow, pod, infinite=infinite)


def app_logs_follow(pod: V1Pod, log_file: str, infinite=False) -> None:
    pod_name = get_name(pod)
    logs(file_exists_in_pod, pod_name, log_file)
    res = shell.call(exec_cmd(pod_name, ['tail', '-n', '+1', '-f', log_file],
                              it=True))
    end_log(res, app_logs_follow, pod, infinite=infinite)


def app_logs(pod: V1Pod, app_type: str = APP_TYPE_WORKER,
             logfile: str = 'info.log', interactive: bool = False,
             follow: bool = False, infinite: bool = False) -> Optional[str]:
    try:
        pod_name = get_name(pod)
        print(pod_name)
        service = get_service_type(pod)
        print(service)
        app = service_and_app_type_to_app(service, app_type)
        log_file = sources_paths.get_logs_file(app, pod_name, logfile)
        if follow:
            app_logs_follow(pod, log_file, infinite=infinite)
        else:
            if not file_exists_in_pod(pod_name, log_file):
                terminal.warning('The log file does not exist. Is the '
                                 'deployment ready?\n'
                                 '    tried: {}'.format(log_file))
            if interactive:
                print('> {}'.format(log_file))
                terminal.horizontal_line()
                shell.call(exec_cmd(pod_name, ['cat', log_file], it=True))
            else:
                return shell.check_output(exec_cmd(pod_name, ['cat', log_file]))
        return None
    except KeyError:
        terminal.error('Only pods hosting onezone or oneprovider '
                       'are supported.')
        return None


def list_logfiles(pod: V1Pod, app_type: str = APP_TYPE_WORKER) -> None:
    pod_name = get_name(pod)
    try:
        service = get_service_type(pod)
        app = service_and_app_type_to_app(service, app_type)
        logs_dir = sources_paths.get_logs_dir(app, pod_name)
        print(shell.check_output(exec_cmd(pod_name, ['ls', logs_dir])))
    except KeyError:
        terminal.error('Only pods hosting onezone or oneprovider '
                       'are supported.')


def match_pods(substring: str) -> List[V1Pod]:
    pods_list = list_pods()
    # Accept dashes as wildcard characters
    pattern = '.*{}.*'.format(substring.replace('-', '.*'))
    return list(filter(lambda pod: re.match(pattern, get_name(pod)),
                       pods_list))


def print_pod_choosing_hint() -> None:
    print('')
    terminal.info('To choose a pod, provide its full name or any '
                  'matching, unambiguous string. You can use dashes '
                  '("{}") for a wildcard character, e.g.: {} will match {}.'
                  .format(terminal.green_str('-'),
                          terminal.green_str('z-1'),
                          terminal.green_str('dev-onezone-node-1-0')))


def match_pod_and_run(pod_substring: str, fun: Callable[..., Optional[Any]],
                      *fun_args, allow_multiple: bool = False) -> Optional[Any]:
    if not pod_substring:
        terminal.error('Please choose a pod:')
        print_pods(list_pods())
        print_pod_choosing_hint()
        return None

    matching_pods = match_pods(pod_substring)

    if not matching_pods:
        pods = list_pods()
        if pods:
            terminal.error('There are no pods matching \'{}\'. '
                           'Choose one of:'.format(pod_substring))
            print_pods(pods)
            print_pod_choosing_hint()
        else:
            terminal.error('There are no pods running')
        return None

    elif len(matching_pods) == 1:
        if fun_args:
            return fun(matching_pods[0], *fun_args)
        return fun(matching_pods[0])

    if allow_multiple:
        for pod in matching_pods:
            fun(pod, fun_args, multiple=True)
    else:
        terminal.error('There is more than one matching pod:')
        print_pods(matching_pods)
        print_pod_choosing_hint()
    return None


def client_alias_to_pod_mapping() -> Dict[str, str]:
    prov_clients_mapping = defaultdict(list)
    client_alias_mapping = {}
    pods_list = list_pods()
    clients_pods = [pod for pod in pods_list
                    if get_service_type(pod) == 'oneclient']
    for client_pod in clients_pods:
        provider = get_client_provider_host(client_pod)
        provider_alias = service_name_to_alias_mapping(provider)
        prov_clients_mapping[provider_alias].append(client_pod)

    i = 1
    for prov_alias in sorted(list(prov_clients_mapping.keys())):
        client_pods = sorted(prov_clients_mapping.get(prov_alias),
                             key=get_name)
        for pod in client_pods:
            key = 'oneclient-{}'.format(i)
            client_alias_mapping[key] = get_name(pod)
            client_alias_mapping[get_name(pod)] = key
            i += 1
    return client_alias_mapping


def create_users(pod_name: str, users: List[str]) -> None:
    """Creates system users on pod specified by 'pod'."""

    def _user_exists(user: str, pod_name: str) -> bool:
        command = ['id', '-u', user]
        ret = subprocess.call(exec_cmd(pod_name, command))

        return ret == 0

    for user in users:
        user_exists = _user_exists(user, pod_name)

        if user_exists:
            print('Skipping creation of user {} - user already exists in {}.'
                  .format(user, pod_name))
        else:
            uid = str(hash(user) % 50000 + 10000)
            command = ['adduser', '--disabled-password', '--gecos', '""',
                       '--uid', uid, user]
            assert subprocess.call(exec_cmd(pod_name, command)) == 0


def create_groups(pod_name: str, groups: Dict[str, List[str]]) -> None:
    """Creates system groups on docker specified by 'container'."""

    def _group_exists(group: str, pod_name: str) -> bool:
        command = ['grep', '-q', group, '/etc/group']
        ret = subprocess.call(exec_cmd(pod_name, command))

        return ret == 0

    for group, users in groups.items():
        group_exists = _group_exists(group, pod_name)
        if group_exists:
            print('Skipping creation of group {} - group already exists in {}.'
                  .format(group, pod_name))
        else:
            gid = str(hash(group) % 50000 + 10000)
            command = ['groupadd', '-g', gid, group]
            assert subprocess.call(exec_cmd(pod_name, command)) == 0
        for user in users:
            command = ['usermod', '-a', '-G', group, user]
            assert subprocess.call(exec_cmd(pod_name, command)) == 0
