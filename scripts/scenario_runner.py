import argparse
import subprocess
import os
import shutil
from time import gmtime, strftime, time
import user_config
import config_generator

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


def run_scenario(scenario, binaries, release_name):

    # TODO: better dealing with time
    one_env_deployment_dir = os.path.join(
        user_config.one_env_directory(),
        'deployment_{}'.format(time()))

    charts_tmp_dir = os.path.join(one_env_deployment_dir, 'charts')
    scenario_tmp = os.path.join(one_env_deployment_dir, scenario)

    os.mkdir(one_env_deployment_dir)

    shutil.copytree('charts', charts_tmp_dir)
    shutil.copytree(scenario, scenario_tmp)

    helm_dep_update_cmd = ['helm', 'dependency', 'update']

    for chart in os.listdir(charts_tmp_dir):
        subprocess.check_call(helm_dep_update_cmd +
                              [os.path.join(charts_tmp_dir, chart)],
                              stderr=subprocess.STDOUT)
    subprocess.check_call(helm_dep_update_cmd + [scenario_tmp],
                          stderr=subprocess.STDOUT)

    helm_install_cmd = ['helm', 'install',
                        os.path.join(one_env_deployment_dir, scenario), '-f',
                        os.path.join(scenario, 'MyValues.yaml'),
                        '--name', release_name]

    # if args.debug:
    helm_install_cmd += ['--debug']

    # TODO: This should be python module
    if binaries:
        config_generator.generate_configs(scenario, one_env_deployment_dir,
                                          os.path.join(scenario_tmp,
                                                       'BinVal.yaml'))

        helm_install_cmd += ['-f', os.path.join(scenario_tmp, 'BinVal.yaml')]

    # if args.config:
    #     helm_install_cmd += ['-f', args.config]

    subprocess.check_call(helm_install_cmd, stderr=subprocess.STDOUT)


if __name__ == '__main__':
    args = parser.parse_args()

    run_scenario(args.scenario, args.binaries, args.release_name)
