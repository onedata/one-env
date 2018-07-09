"""
Brings up onedata environment described in given scenario
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"


import re
import os
import yaml
import shutil
import subprocess

import helm
import pods
import console
import user_config
import config_parser
import config_generator
from config import readers, writers


STABLE_PATH = 'stable'
SOURCES_READY_FILE_PATH = '/tmp/sources_ready.txt'
CROSS_SUPPORT_JOB = 'cross-support-job-3p'


def get_scenario_key(deployment_charts_path: str):
    requirements = readers.ConfigReader(
        os.path.join(deployment_charts_path, STABLE_PATH, CROSS_SUPPORT_JOB,
                     'requirements.yaml')
    ).load()

    scenario_key = ''

    for req in requirements.get('dependencies'):
        if re.match('onedata-\d+p', req.get('name')):
            scenario_key = req.get('name')
            break

    return scenario_key


def change_requirements(log_file, deployment_charts_path: str):
    change_req_cmd = ['./repository-dev.sh']
    subprocess.check_call(change_req_cmd, cwd=os.path.join(
        deployment_charts_path, STABLE_PATH), stdout=log_file,
                          stderr=subprocess.STDOUT)


def update_charts_dependencies(deployment_charts_path: str,
                               log_directory_path: str, local: bool):
    make_charts_cmd = ['make', CROSS_SUPPORT_JOB]
    log_file_path = os.path.join(log_directory_path, 'helm_dep_update.log')
    console.info('Updating charts dependencies. Writing logs to {}'.
                 format(log_file_path))

    with open(log_file_path, 'w') as log_file:
        if local:
            change_requirements(log_file, deployment_charts_path)
        subprocess.check_call(make_charts_cmd, cwd=os.path.join(
            deployment_charts_path, STABLE_PATH), stdout=log_file,
                              stderr=subprocess.STDOUT)


def rsync_sources(deployment_dir: str, log_directory_path: str):
    with open(os.path.join(deployment_dir, 'deployment_data.yml')) as \
            deployment_data_file:
        deployment_data = yaml.load(deployment_data_file)
        log_file_path = os.path.join(log_directory_path, 'rsync_up.log')

        for pod_name in deployment_data.get('sources'):
            panel_from_sources = False
            pod = pods.match_pods(pod_name)[0]
            service_name = '-'.join(pods.get_service_name(pod).split('-')[1:])
            node_name = 'n{}'.format(pods.get_node_num(pod_name))
            generated_app_config_path = os.path.join(deployment_dir,
                                                     service_name,
                                                     node_name,
                                                     'app.config')
            panel_name = 'oz_panel' if 'zone' in service_name else 'op_panel'

            pods.wait_for_pod(pod)
            pod_cfg = deployment_data.get('sources').get(pod_name).items()

            with open(log_file_path, 'w') as log_file:
                for source, source_path in pod_cfg:
                    build_path = os.path.join(source_path, '_build')
                    destination_path = '{}:{}'.format(pod_name, source_path)
                    mkdir_cmd = ['bash', '-c', 'mkdir -p {}'.format(build_path)]
                    subprocess.call(pods.cmd_exec(pod_name, mkdir_cmd))
                    subprocess.call(pods.cmd_rsync(build_path, destination_path),
                                    shell=True, stdout=log_file)

                    if 'panel' in source:
                        source_app_config_path = os.path.join(
                            build_path, 'default/rel/{}/data'.format(panel_name))
                        destination_path = '{}:{}'.format(pod_name,
                                                          source_app_config_path)
                        subprocess.call(pods.cmd_rsync(generated_app_config_path,
                                                       destination_path),
                                        shell=True, stdout=log_file)
                        panel_from_sources = True
                        panel_path = source_path

                if not panel_from_sources:
                    destination_path = '{}:/var/lib/{}/app.config'.format(pod_name,
                                                                          panel_name)
                    subprocess.call(pods.cmd_rsync(generated_app_config_path,
                                                   destination_path),
                                    shell=True, stdout=log_file)
                    create_ready_file_cmd = ['bash', '-c', 'touch {}'
                        .format(SOURCES_READY_FILE_PATH)]
                    subprocess.call(pods.cmd_exec(pod_name, create_ready_file_cmd))
                else:
                    create_ready_file_cmd = ['bash', '-c', 'echo {} >> {}'
                        .format(panel_path, SOURCES_READY_FILE_PATH)]
                    subprocess.call(pods.cmd_exec(pod_name, create_ready_file_cmd))


def run_scenario(deployment_dir: str, local: bool, debug: bool, dry_run: bool):
    env_cfg = readers.ConfigReader(os.path.join(deployment_dir,
                                                'env_config.yaml')).load()
    original_scenario_path = os.path.join('scenarios', env_cfg.get('scenario'))
    deployment_charts_path = os.path.join(deployment_dir, 'charts')
    deployment_logdir_path = os.path.join(deployment_dir, 'logs')
    deployment_scenario_path = os.path.join(deployment_dir,
                                            original_scenario_path)
    base_sources_cfg_path = os.path.join(deployment_scenario_path,
                                         'SourcesVal.yaml')

    shutil.copytree('charts', deployment_charts_path)
    shutil.copytree(original_scenario_path, deployment_scenario_path)
    os.mkdir(deployment_logdir_path)

    base_sources_cfg = readers.ConfigReader(base_sources_cfg_path).load()
    scenario_key = get_scenario_key(deployment_charts_path)
    update_charts_dependencies(deployment_charts_path, deployment_logdir_path,
                               local)

    config_parser.parse_env_config(env_cfg, base_sources_cfg, scenario_key,
                                   deployment_scenario_path)

    my_values_path = os.path.join(deployment_scenario_path, 'MyValues.yaml')
    custom_config_path = os.path.join(deployment_scenario_path,
                                      'CustomConfig.yaml')
    helm_install_cmd = helm.cmd_install(CROSS_SUPPORT_JOB, [my_values_path,
                                                            custom_config_path])

    if debug:
        helm_install_cmd.extend(['--debug'])
    if dry_run:
        helm_install_cmd.extend(['--dry-run'])

    if env_cfg.get('sources'):
        config_generator.generate_configs(base_sources_cfg,
                                          base_sources_cfg_path,
                                          scenario_key, deployment_dir)

        helm_install_cmd.extend(['-f', base_sources_cfg_path])

    subprocess.check_call(helm_install_cmd, cwd=os.path.join(
            deployment_charts_path, STABLE_PATH), stderr=subprocess.STDOUT)

    rsync_sources(deployment_dir, deployment_logdir_path)
