import argparse
import subprocess
import os
import shutil
import user_config
import config_generator
from config import readers, writers
import console
import collections


parser = argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    description='Bring up onedata environment.')

parser.add_argument(
    '-b', '--binaries',
    action='store_true',
    help='',
    dest='binaries')


def providers_mapping(name):
    return {'oneprovider-krakow': 'oneprovider-p1',
            'oneprovider-paris': 'oneprovider-p2'}.get(name, name)


def parse_nodes(env_cfg, service):
    nodes = set(env_cfg[service]['clusterConfig']['managers'] +
                env_cfg[service]['clusterConfig']['workers'] +
                env_cfg[service]['clusterConfig']['databases'])

    nodes = {node_name: {} for node_name in nodes}
    return nodes


def modify_config(scenario_key, env_cfg, env_config_scenario_path, bin_cfg,
                  binaries):
    new_env_cfg = {scenario_key: dict()}

    # get global variables
    force_image_pull = env_cfg.get('forceImagePull')
    oneprovider_image = env_cfg.get('oneproviderImage')
    onezone_image = env_cfg.get('onezoneImage')
    create_spaces = env_cfg.get('createSpaces', True)

    if not create_spaces:
        new_env_cfg['spaces'] = []

    for service in bin_cfg[scenario_key].keys():
        new_env_cfg[scenario_key][service] = \
            {'image': onezone_image if 'onezone' in service else oneprovider_image}

        new_env_cfg[scenario_key][service]['imagePullPolicy'] = \
            'Always' if force_image_pull else 'IfNotPresent'
        #
        # if not env_cfg[providers_mapping(service)].get('createUsers', True):
        #     new_env_cfg[scenario_key][service]['batchConfig']['onepanelAdminUsers'] = {}
        #     new_env_cfg[scenario_key][service]['batchConfig'][
        #         'onepanelUsers'] = {}

        if env_cfg.get(providers_mapping(service)):
            if not binaries and env_cfg[service].get('clusterConfig'):
                new_env_cfg[scenario_key][service]['nodes'] = \
                    parse_nodes(env_cfg, providers_mapping(service))
            new_env_cfg[scenario_key][service] = {**new_env_cfg[scenario_key][service], **env_cfg[providers_mapping(service)]}

    writer = writers.ConfigWriter(new_env_cfg, 'yaml')
    with open(os.path.join(env_config_scenario_path, 'env_config.yaml'), "w") as f:
        f.write(writer.dump())


def get_scenario_key(env_config_scenario_path):
    r = readers.ConfigReader(os.path.join(env_config_scenario_path,
                                          'requirements.yaml'))
    requirements = r.load()

    scenario_key = ""

    for req in requirements.get('dependencies'):
        for tag in req.get('tags', []):
            if 'scenario-key' in tag:
                scenario_key = req.get('name')

    return scenario_key


def update_charts_dependencies(env_config_charts_path, env_config_scenario_path,
                               log_directory):
    helm_dep_update_cmd = ['helm', 'dependency', 'update']
    console.info('updating charts dependencies')

    with open(os.path.join(log_directory, 'helm_dep_update.log'), 'w') as f:
        for chart in os.listdir(env_config_charts_path):
            subprocess.check_call(helm_dep_update_cmd +
                                  [os.path.join(env_config_charts_path, chart)],
                                  stdout=f, stderr=subprocess.STDOUT)
        subprocess.check_call(helm_dep_update_cmd + [env_config_scenario_path],
                              stdout=f, stderr=subprocess.STDOUT)


def parse_custom_binaries_config(custom_binaries_cfg, base_binaries_cfg,
                                 scenario_key, env_config_scenario_path,
                                 env_cfg):
    for service in base_binaries_cfg[scenario_key]:
        nodes = {}

        if env_cfg[providers_mapping(service)].get('clusterConfig'):
            nodes = parse_nodes(env_cfg, service)

        for node_name, node_binaries in custom_binaries_cfg[providers_mapping(service)].items():
            node = {'binaries': [{'name': binary} for binary in node_binaries]}
            nodes[node_name] = node
        base_binaries_cfg[scenario_key][service]['nodes'] = nodes

    writer = writers.ConfigWriter(base_binaries_cfg, 'yaml')
    with open(os.path.join(env_config_scenario_path, 'BinVal.yaml'), "w") as f:
        f.write(writer.dump())


def run_scenario(env_config_dir_path):
    env_cfg = readers.ConfigReader(os.path.join(env_config_dir_path,
                                   'env_config.yaml')).load()
    original_scenario_path = os.path.join('scenarios', env_cfg.get('scenario'))
    env_config_charts_path = os.path.join(env_config_dir_path, 'charts')
    log_dir = os.path.join(env_config_dir_path, 'logs')
    env_config_scenario_path = os.path.join(env_config_dir_path,
                                            original_scenario_path)
    # TODO: BinVals hardcoded
    bin_cfg_path = os.path.join(env_config_scenario_path, 'BinVal.yaml')

    shutil.copytree('charts', env_config_charts_path)
    shutil.copytree(original_scenario_path, env_config_scenario_path)
    os.mkdir(log_dir)

    bin_cfg = readers.ConfigReader(bin_cfg_path).load()
    scenario_key = get_scenario_key(env_config_scenario_path)
    update_charts_dependencies(env_config_charts_path, env_config_scenario_path,
                               log_dir)

    # TODO: organize values files
    helm_install_cmd = ['helm', 'install', env_config_scenario_path, '-f',
                        os.path.join(env_config_scenario_path, 'MyValues.yaml'),
                        '--name', user_config.get('helmDeploymentName')]

    if env_cfg.get('binaries'):
        if isinstance(env_cfg.get('binaries'), dict):
            parse_custom_binaries_config(env_cfg.get('binaries'), bin_cfg,
                                         scenario_key, env_config_scenario_path,
                                         env_cfg)

        config_generator.generate_configs(bin_cfg, bin_cfg_path,
                                          env_config_dir_path, scenario_key)

        helm_install_cmd += ['-f', os.path.join(bin_cfg_path)]

    modify_config(scenario_key, env_cfg, env_config_scenario_path, bin_cfg,
                  env_cfg.get('binaries'))

    helm_install_cmd += ['-f', os.path.join(env_config_scenario_path,
                                            'env_config.yaml')]

    subprocess.check_call(helm_install_cmd, stderr=subprocess.STDOUT)
#
# if __name__ == '__main__':
#     args = parser.parse_args()
#
#     run_scenario(args.scenario, args.binaries, args.release_name)
