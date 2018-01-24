import argparse
import subprocess
import os
import shutil
from time import gmtime, strftime, time
import user_config
import config_generator
from config import readers, writers

parser = argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    description='Bring up onedata environment.')

parser.add_argument(
    '-b', '--binaries',
    action='store_true',
    help='',
    dest='binaries')

parser.add_argument(
    '-s', '--scenario',
    action='store',
    help='',
    required=False,
    default='../scenarios/scenario-1oz-1op',
    dest='scenario')

parser.add_argument(
    '-r', '--release',
    action='store',
    help='',
    required=False,
    default='develop',
    dest='release_name'
)

parser.add_argument(
    '-d', '--debug',
    action='store_true',
    help='',
    dest='debug'
)

parser.add_argument(
    '-c', '--config',
    action='store',
    help='',
    dest='config'
)


def providers_mapping(name):
    return {'oneprovider-krakow': 'oneprovider-p1',
            'oneprovider-paris': 'oneprovider-p2'}.get(name, name)


def modify_config(scenario_key, env_cfg, env_config_scenario_path, bin_cfg):
    new_env_cfg = {scenario_key: dict()}

    # get global variables
    force_image_pull = env_cfg.get('forceImagePull')
    oneprovider_image = env_cfg.get('oneproviderImage')
    onezone_image = env_cfg.get('onezoneImage')

    for service in bin_cfg[scenario_key].keys():
        new_env_cfg[scenario_key][service] = \
            {'image': onezone_image if 'onezone' in service else oneprovider_image}

        new_env_cfg[scenario_key][service]['imagePullPolicy'] = \
            'Always' if force_image_pull else 'IfNotPresent'

        if env_cfg.get(service):
            new_env_cfg[scenario_key][service] = env_cfg[service]

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
            if 'bin-vals' in tag:
                scenario_key = req.get('name')

    return scenario_key


def update_charts_dependencies(env_config_charts_path, env_config_scenario_path):
    helm_dep_update_cmd = ['helm', 'dependency', 'update']

    for chart in os.listdir(env_config_charts_path):
        subprocess.check_call(helm_dep_update_cmd +
                              [os.path.join(env_config_charts_path, chart)],
                              stderr=subprocess.STDOUT)
    subprocess.check_call(helm_dep_update_cmd + [env_config_scenario_path],
                          stderr=subprocess.STDOUT)


def parse_custom_binaries_config(custom_binaries_cfg, base_binaries_cfg,
                                 scenario_key, env_config_scenario_path):
    for service in base_binaries_cfg[scenario_key]:
        nodes = []
        for node_name, node_binaries in custom_binaries_cfg[providers_mapping(service)].items():
            node = {'name': node_name,
                    'binaries': [{'name': binary} for binary in node_binaries]}
            nodes.append(node)
        base_binaries_cfg[scenario_key][service]['nodes'] = nodes

    writer = writers.ConfigWriter(base_binaries_cfg, 'yaml')
    with open(os.path.join(env_config_scenario_path, 'BinVal.yaml'), "w") as f:
        f.write(writer.dump())


def run_scenario(env_config_dir_path):
    env_cfg = readers.ConfigReader(os.path.join(env_config_dir_path,
                                   'env_config.yaml')).load()
    original_scenario_path = os.path.join('scenarios', env_cfg.get('scenario'))
    env_config_charts_path = os.path.join(env_config_dir_path, 'charts')
    env_config_scenario_path = os.path.join(env_config_dir_path,
                                            original_scenario_path)

    shutil.copytree('charts', env_config_charts_path)
    shutil.copytree(original_scenario_path, env_config_scenario_path)

    bin_cfg = readers.ConfigReader(os.path.join(env_config_scenario_path,
                                                'BinVal.yaml')).load()
    scenario_key = get_scenario_key(env_config_scenario_path)
    update_charts_dependencies(env_config_charts_path, env_config_scenario_path)

    # TODO: organize values files
    helm_install_cmd = ['helm', 'install', env_config_scenario_path, '-f',
                        os.path.join(env_config_scenario_path, 'MyValues.yaml'),
                        '--name', user_config.get('helmDeploymentName')]

    # TODO: BinVals hardcoded
    if env_cfg.get('binaries'):
        if isinstance(env_cfg.get('binaries'), dict):
            parse_custom_binaries_config(env_cfg.get('binaries'), bin_cfg,
                                         scenario_key, env_config_scenario_path)

        config_generator.generate_configs(env_config_scenario_path,
                                          env_config_dir_path,
                                          os.path.join(env_config_scenario_path,
                                                       'BinVal.yaml'),
                                          env_cfg, scenario_key)

        helm_install_cmd += ['-f', os.path.join(env_config_scenario_path,
                                                'BinVal.yaml')]

    modify_config(scenario_key, env_cfg, env_config_scenario_path, bin_cfg)

    helm_install_cmd += ['-f', os.path.join(env_config_scenario_path,
                                            'env_config.yaml'), '--debug']

    # if args.config:
    #     helm_install_cmd += ['-f', args.config]

    subprocess.check_call(helm_install_cmd, stderr=subprocess.STDOUT)

#
# if __name__ == '__main__':
#     args = parser.parse_args()
#
#     run_scenario(args.scenario, args.binaries, args.release_name)
