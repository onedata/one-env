"""
Part of onenv tool that allows upgrade Onezone or Oneprovider service (started
either from sources or packages). After upgrade, all service pods are restarted
and sources are rsynced. It is also possible to upgrade helm deployment itself.
For more information refer to script's help.
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2019 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import argparse
from typing import List, Tuple, Optional

import yaml
from kubernetes.client import V1Pod, V1StatefulSet

from .utils.k8s import helm, pods
from .utils import arg_help_formatter
from .utils.deployment.node import Node
from .utils.common import get_curr_time
from .utils.yaml_utils import dump_yaml
from .utils.one_env_dir import user_config
from .utils.terminal import error, warning
from .utils.shell import call, check_output
from .utils.names_and_paths import ONEDATA_3P
from .utils.one_env_dir import deployments_dir
from .utils.deployment.sources import rsync_sources
from .utils.k8s.kubernetes_utils import get_chart_name
from .utils.k8s.kubernetes_utils import match_components_verbose, get_name
from .utils.k8s.stateful_sets import list_stateful_sets, get_stateful_set_pods


def upgrade_deployment_cmd(files_paths: Optional[List[str]] = None,
                           set_values: Optional[helm.SetValues] = None,
                           charts_path: Optional[str] = None) -> List[str]:
    dump_prev_values_to_file()
    if files_paths:
        values_files = [deployments_dir.get_prev_values_path()] + files_paths
    else:
        values_files = [deployments_dir.get_prev_values_path()]
    return helm.upgrade_cmd(values_files=values_files,
                            set_values=set_values,
                            charts_path=charts_path)


def upgrade_stateful_set(stateful_set: V1StatefulSet,
                         set_values: List[Tuple[str, str]],
                         local_charts_path: Optional[str],
                         show_diff: bool) -> None:
    cmd = upgrade_deployment_cmd(set_values=set_values,
                                 charts_path=local_charts_path)
    if show_diff:
        diff(cmd)
    else:
        call(cmd)
        rsync_sources_for_pods(get_stateful_set_pods(stateful_set))


def upgrade_deployment(file_path: str,
                       set_values: Optional[helm.SetValues] = None,
                       local_charts_path: Optional[str] = None,
                       show_diff: bool = False) -> None:
    cmd = upgrade_deployment_cmd(files_paths=[file_path],
                                 set_values=set_values,
                                 charts_path=local_charts_path)
    if show_diff:
        diff(cmd)
    else:
        call(cmd)
        rsync_sources_for_pods(pods.list_pods())


def rollback(version: str, show_diff: bool) -> None:
    cmd = helm.rollback_cmd(version)
    if show_diff:
        if version == '0':
            warning('helm diff plugin does not work with version number 0 '
                    'in rollback.')
        diff(cmd)
    else:
        call(cmd)
        rsync_sources_for_pods(pods.list_pods())


def rsync_sources_for_pods(pod_list: List[V1Pod], timeout: int = 60) -> None:
    nodes_cfg = {}
    for pod in pod_list:
        node = Node.from_deployment_data(get_name(pod),
                                         get_chart_name(pod))
        node.add_node_to_nodes_cfg(nodes_cfg)
    rsync_sources(deployments_dir.get_current_deployment_dir(),
                  deployments_dir.get_current_log_dir(), nodes_cfg, timeout,
                  rsync_persistence_dirs=False)


def dump_prev_values_to_file() -> None:
    prev_values = yaml.load(check_output(helm.get_values_cmd()))
    deployments_dir.ensure_upgrade_data_dir_exists()
    dump_yaml(prev_values, deployments_dir.get_prev_values_path())


def parse_set_values(image: str, sources: bool,
                     stateful_set: V1StatefulSet) -> List[Tuple[str, str]]:
    set_values = []
    chart_name = get_chart_name(stateful_set)

    if image:
        set_values.append(('image', image))

    if sources:
        set_values.append(('deployFromSources.timestamp', get_curr_time()))

    set_values = [('{}.{}.{}'.format(ONEDATA_3P, chart_name, key), val)
                  for (key, val) in set_values]
    return set_values


def diff(cmd: List[str]) -> None:
    # get rid of `helm` in cmd, as helm diff will be added at the beginning
    call(helm.diff_cmd(cmd[1:]))


def main() -> None:
    upgrade_args_parser = argparse.ArgumentParser(
        prog='onenv upgrade',
        formatter_class=arg_help_formatter.ArgumentsHelpFormatter,
        description='Upgrades / rollbacks Onezone/Oneprovider service or '
                    'whole helm deployment.'
    )

    type_group = upgrade_args_parser.add_mutually_exclusive_group()

    upgrade_args_parser.add_argument(
        '-i', '--image',
        help='image to use when upgrading image for service.',
        default=''
    )

    type_group.add_argument(
        help='stateful set name (or matching pattern, use "-" for wildcard). '
             'To list stateful sets use "kubectl get statefulset" command',
        dest='stateful_set_substring',
        nargs='?',
        default=None
    )

    type_group.add_argument(
        '-r', '--rollback',
        action='store_true',
        help='if specified rollback to one of the previous deployment '
             'versions (revisions) will be performed.'
    )

    upgrade_args_parser.add_argument(
        '-s', '--sources',
        action='store_true',
        help='if specified updates timestamp for sources in charts. This '
             'triggers restarting service pods and it is required if the only '
             'change between deployments is change in sources.'
    )

    upgrade_args_parser.add_argument(
        '-v', '--rollback-version',
        help='deployment version to which rollback should be performed. '
             'By default rollback to previous version is performed.',
        default='0',
        dest='rollback_version'
    )

    upgrade_args_parser.add_argument(
        '-y', '--yaml-values',
        help='yaml file with values for helm deployment'
    )

    upgrade_args_parser.add_argument(
        '-d', '--show-diff',
        help='prints difference between current deployment and deployment '
             'after upgrade / rollback. Requires helm diff plugin (see README '
             'for more information).',
        action='store_true',
        dest='show_diff'
    )

    upgrade_args_parser.add_argument(
        '-lcp', '--local-charts-path',
        help='path to local charts',
        dest='local_charts_path'
    )

    upgrade_args = upgrade_args_parser.parse_args()

    user_config.ensure_exists()
    helm.ensure_deployment(exists=True, fail_with_error=True)

    local_charts_path = upgrade_args.local_charts_path
    stateful_set_substring = upgrade_args.stateful_set_substring
    show_diff = upgrade_args.show_diff

    if stateful_set_substring:
        if any([upgrade_args.sources, upgrade_args.image]):
            stateful_set = match_components_verbose(stateful_set_substring,
                                                    list_stateful_sets)
            set_values = parse_set_values(upgrade_args.image,
                                          upgrade_args.sources,
                                          stateful_set)
            if stateful_set is None:
                exit(1)

            if upgrade_args.yaml_values:
                upgrade_deployment(upgrade_args.yaml_values, set_values,
                                   local_charts_path, show_diff)
            else:
                upgrade_stateful_set(stateful_set, set_values,
                                     local_charts_path, show_diff)
        else:
            error('--sources or --image option has to be specified when '
                  'stateful set is given.')
            exit(1)

    elif upgrade_args.yaml_values:
        upgrade_deployment(upgrade_args.yaml_values,
                           local_charts_path=local_charts_path,
                           show_diff=show_diff)

    elif upgrade_args.rollback:
        rollback(upgrade_args.rollback_version, show_diff)


if __name__ == '__main__':
    main()
