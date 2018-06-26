"""
Brings up onedata environment described in given scenario
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"


import subprocess
import os
import shutil
import user_config
import config_generator
from config import readers, writers
import console
import config_parser
import re
import pods
import time
from onenv_rsync import rsync
import yaml


def get_scenario_key(deployment_scenario_path: str):
    requirements = readers.ConfigReader(
        os.path.join(deployment_scenario_path, 'requirements.yaml')
    ).load()

    scenario_key = ''

    for req in requirements.get('dependencies'):
        if re.match('onedata-\d+p', req.get('name')):
            scenario_key = req.get('name')

    return scenario_key


def update_charts_dependencies(env_config_charts_path, env_config_scenario_path,
                               log_directory):
    helm_dep_update_cmd = ['helm', 'dependency', 'update']
    log_file = os.path.join(log_directory, 'helm_dep_update.log')
    console.info('Updating charts dependencies. Writing logs to {}'.
                 format(log_file))

    with open(log_file, 'w') as f:
        for chart in os.listdir(env_config_charts_path):
            subprocess.check_call(helm_dep_update_cmd +
                                  [os.path.join(env_config_charts_path, chart)],
                                  stdout=f, stderr=subprocess.STDOUT)
        subprocess.check_call(helm_dep_update_cmd + [env_config_scenario_path],
                              stdout=f, stderr=subprocess.STDOUT)


def run_scenario(deployment_dir: str):
    env_cfg = readers.ConfigReader(os.path.join(deployment_dir,
                                                'env_config.yaml')).load()
    original_scenario_path = os.path.join('scenarios', env_cfg.get('scenario'))
    deployment_charts_path = os.path.join(deployment_dir, 'charts')
    deployment_logdir = os.path.join(deployment_dir, 'logs')
    deployment_scenario_path = os.path.join(deployment_dir,
                                            original_scenario_path)

    # TODO: Change values files after charts integration
    base_sources_cfg_path = os.path.join(deployment_scenario_path,
                                         'SourcesVal.yaml')

    shutil.copytree('charts', deployment_charts_path)
    shutil.copytree(original_scenario_path, deployment_scenario_path)
    shutil.copy('scripts/parse_sources.py', deployment_dir)
    os.mkdir(deployment_logdir)

    base_sources_cfg = readers.ConfigReader(base_sources_cfg_path).load()
    scenario_key = get_scenario_key(deployment_scenario_path)
    update_charts_dependencies(deployment_charts_path, deployment_scenario_path,
                               deployment_logdir)

    config_parser.parse_env_config(env_cfg, base_sources_cfg, scenario_key,
                                   deployment_scenario_path)

    helm_install_cmd = ['helm', 'install', '--namespace', user_config.get('namespace'),
                        deployment_scenario_path, '-f',
                        os.path.join(deployment_scenario_path, 'MyValues.yaml'),
                        '--name', user_config.get('helmDeploymentName')]

    helm_install_cmd += ['-f', os.path.join(deployment_scenario_path,
                                            'CustomConfig.yaml')]

    if env_cfg.get('sources'):
        config_generator.generate_configs(base_sources_cfg,
                                          base_sources_cfg_path,
                                          scenario_key, deployment_dir)

        helm_install_cmd += ['-f', os.path.join(base_sources_cfg_path)]

    subprocess.check_call(helm_install_cmd, stderr=subprocess.STDOUT)
