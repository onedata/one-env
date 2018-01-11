import argparse
import subprocess
import os
import shutil
import time

parser = argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    description='Bring up onedata environment.')

parser.add_argument(
    '-b', '--binaries',
    action='store_true',
    help='',
    required=False,
    dest='binaries')

parser.add_argument(
    '-s', '--scenario',
    action='store',
    help='',
    required=False,
    default='scenarios/scenario-1oz-1op',
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

if __name__ == '__main__':
    args = parser.parse_args()

    one_env_tmp_dir = '/tmp/one_env{}'.format(time.time())
    charts_tmp_dir = os.path.join(one_env_tmp_dir, 'charts')
    scenario_tmp = os.path.join(one_env_tmp_dir, args.scenario)

    os.mkdir(one_env_tmp_dir)

    shutil.copytree('charts', charts_tmp_dir)
    shutil.copytree(args.scenario, scenario_tmp)

    helm_dep_update_cmd = ['helm', 'dependency', 'update']

    for chart in os.listdir(charts_tmp_dir):
        subprocess.check_call(helm_dep_update_cmd +
                              [os.path.join(charts_tmp_dir, chart)])
    subprocess.check_call(helm_dep_update_cmd + [scenario_tmp])

    helm_install_cmd = ['helm', 'install',
                        os.path.join(one_env_tmp_dir, args.scenario), '-f',
                        os.path.join(args.scenario, 'MyValues.yaml'),
                        '--name', args.release_name]

    if args.debug:
        helm_install_cmd += ['--debug']

    if args.binaries:
        subprocess.check_call(['python3', 'config_generator.py', '--c',
                               os.path.join(scenario_tmp, 'BinVal.yaml')])

        helm_install_cmd += ['-f', os.path.join(scenario_tmp, 'BinVal.yaml')]

    subprocess.check_call(helm_install_cmd, stderr=subprocess.STDOUT)
