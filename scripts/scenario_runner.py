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


def get_scenario_key(env_config_scenario_path):
    requirements = readers.ConfigReader(
        os.path.join(env_config_scenario_path, 'requirements.yaml')
    ).load()

    scenario_key = ""

    for req in requirements.get('dependencies'):
        for tag in req.get('tags', []):
            if 'scenario-key' in tag:
                scenario_key = req.get('name')

    return scenario_key


def update_charts_dependencies(env_config_charts_path, env_config_scenario_path,
                               log_directory):
    helm_dep_update_cmd = ['helm', 'dependency', 'update']
    console.info('Updating charts dependencies')

    with open(os.path.join(log_directory, 'helm_dep_update.log'), 'w') as f:
        for chart in os.listdir(env_config_charts_path):
            subprocess.check_call(helm_dep_update_cmd +
                                  [os.path.join(env_config_charts_path, chart)],
                                  stdout=f, stderr=subprocess.STDOUT)
        subprocess.check_call(helm_dep_update_cmd + [env_config_scenario_path],
                              stdout=f, stderr=subprocess.STDOUT)


def run_scenario(env_config_dir_path):
    env_cfg = readers.ConfigReader(os.path.join(env_config_dir_path,
                                   'env_config.yaml')).load()
    original_scenario_path = os.path.join('scenarios', env_cfg.get('scenario'))
    env_config_charts_path = os.path.join(env_config_dir_path, 'charts')
    log_dir = os.path.join(env_config_dir_path, 'logs')
    env_config_scenario_path = os.path.join(env_config_dir_path,
                                            original_scenario_path)

    # TODO: Change values files after charts integration
    bin_cfg_path = os.path.join(env_config_scenario_path, 'BinVal.yaml')

    shutil.copytree('charts', env_config_charts_path)
    shutil.copytree(original_scenario_path, env_config_scenario_path)
    os.mkdir(log_dir)

    bin_cfg = readers.ConfigReader(bin_cfg_path).load()
    scenario_key = get_scenario_key(env_config_scenario_path)
    update_charts_dependencies(env_config_charts_path, env_config_scenario_path,
                               log_dir)

    config_parser.parse_env_config(env_cfg, bin_cfg, scenario_key,
                                   env_config_scenario_path)

    helm_install_cmd = ['helm', 'install', env_config_scenario_path, '-f',
                        os.path.join(env_config_scenario_path, 'MyValues.yaml'),
                        '--name', user_config.get('helmDeploymentName')]

    helm_install_cmd += ['-f', os.path.join(env_config_scenario_path,
                                            'CustomConfig.yaml')]

    if env_cfg.get('binaries'):
        config_generator.generate_configs(bin_cfg, bin_cfg_path, scenario_key,
                                          env_config_dir_path)

        helm_install_cmd += ['-f', os.path.join(bin_cfg_path)]

    subprocess.check_call(helm_install_cmd, stderr=subprocess.STDOUT)
