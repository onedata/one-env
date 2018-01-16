import argparse
import subprocess
import os
import shutil
from time import gmtime, strftime, time
import user_config
import config_generator
from config import readers

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


def run_scenario(env_config_dir_path):
    reader = readers.ConfigReader(os.path.join(env_config_dir_path,
                                  'env_config.yaml'))
    env_cfg = reader.load()

    original_scenario_path = os.path.join('scenarios', env_cfg.get('scenario'))

    env_config_charts_path = os.path.join(env_config_dir_path, 'charts')
    env_config_scenario_path = os.path.join(env_config_dir_path,
                                            original_scenario_path)

    shutil.copytree('charts', env_config_charts_path)
    shutil.copytree(original_scenario_path, env_config_scenario_path)

    helm_dep_update_cmd = ['helm', 'dependency', 'update']

    for chart in os.listdir(env_config_charts_path):
        subprocess.check_call(helm_dep_update_cmd +
                              [os.path.join(env_config_charts_path, chart)],
                              stderr=subprocess.STDOUT)
    subprocess.check_call(helm_dep_update_cmd + [env_config_scenario_path],
                          stderr=subprocess.STDOUT)

    # TODO: configure release name
    helm_install_cmd = ['helm', 'install', env_config_scenario_path, '-f',
                        os.path.join(env_config_scenario_path, 'MyValues.yaml'),
                        '--name', 'develop']

    # if args.debug:
    helm_install_cmd += ['--debug']

    # TODO: BinVals hardcoded
    if env_cfg.get('binaries'):
        config_generator.generate_configs(env_config_scenario_path,
                                          env_config_dir_path,
                                          os.path.join(env_config_scenario_path,
                                                       'BinVal.yaml'))

        helm_install_cmd += ['-f', os.path.join(env_config_scenario_path,
                                                'BinVal.yaml')]

    # if args.config:
    #     helm_install_cmd += ['-f', args.config]

    subprocess.check_call(helm_install_cmd, stderr=subprocess.STDOUT)

#
# if __name__ == '__main__':
#     args = parser.parse_args()
#
#     run_scenario(args.scenario, args.binaries, args.release_name)
