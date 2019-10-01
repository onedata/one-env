"""
Part of onenv tool that allows to download artifacts from repository.
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2019 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import os
import sys
import subprocess as sp
import argparse
import datetime
from typing import Any, Dict, Tuple, Optional

import boto3
from paramiko import SSHClient, AutoAddPolicy

from . import ONE_ENV_ROOT_DIR
from .utils.shell import check_output
from .utils import arg_help_formatter
from .utils.yaml_utils import dump_yaml
from .utils.terminal import info, warning, error, horizontal_line
from .utils.deployment.sources_paths import (get_sources_location,
                                             get_onepanel_sources_locations)
from .utils.common import (unpack_tar, get_git_branch_cmd,
                           find_files_in_relative_paths, get_git_repo)
from .utils.artifacts.branch_config import (branch_config_template_path,
                                            coalesce_branch_config)
from .utils.artifacts import (CURRENT_BRANCH, DEFAULT_BRANCH,
                              LOCAL_ARTIFACTS_DIR, ARTIFACT_REPO_HOST_ENV,
                              ARTIFACT_REPO_PORT_ENV)
from .utils.artifacts.download_artifact import (download_artifact_safe,
                                                download_specific_or_default,
                                                artifact_tar_name,
                                                s3_download_artifact_safe,
                                                s3_download_specific_or_default)


def ssh_to_artifact_repo(hostname: str, port: int, username: str) -> SSHClient:
    ssh = SSHClient()
    ssh.set_missing_host_key_policy(AutoAddPolicy())
    ssh.load_system_host_keys()
    ssh.connect(hostname, port=port, username=username)
    return ssh


def get_s3_resource(s3_url: str) -> boto3.resource:
    s3_session = boto3.session.Session()
    return s3_session.resource(
        service_name='s3',
        endpoint_url=s3_url
    )


def get_current_branch() -> Optional[str]:
    branch_name = None
    cwd = os.getcwd()
    try:
        branch_name = get_git_branch_cmd(cwd)
    except sp.CalledProcessError:
        warning('Could not get branch from parent repository. Will use '
                'default branch.')
    return branch_name


def s3_download_missing_artifact(*, s3_res: boto3.resource, bucket: str,
                                 branch: str, plan: str, target_dir: str,
                                 current_branch: str, default_branch: str):
    if branch != CURRENT_BRANCH:
        # user set branch for particular repo - print info, try download
        # artifact
        info('Getting artifact for plan {}\'s from branch {}'
             .format(plan, branch))
        exc_log = ('Branch {} in plan {} not found. Exiting...'
                   .format(branch, plan))
        res = s3_download_artifact_safe(s3_res=s3_res,
                                        bucket=bucket,
                                        branch=branch,
                                        plan=plan,
                                        local_path=target_dir,
                                        exc_log=exc_log,
                                        exc_handler=sys.exit,
                                        exc_handler_pos_args=(1, ))
    else:
        # user didn't set particular branch - print info about branches,
        # try download artifact
        info('Trying to download artifact for plan {}\'s from branch {}. '
             'On failure artifact from {} branch will be downloaded.'
             .format(plan, current_branch, default_branch))

        res = s3_download_specific_or_default(s3_res=s3_res,
                                              bucket=bucket,
                                              plan=plan,
                                              branch=current_branch,
                                              default_branch=default_branch,
                                              local_path=target_dir)
    return res


def download_missing_artifact(*, plan: str, branch: str, ssh: SSHClient,
                              hostname: str, port: int, username: str,
                              default_branch: str, current_branch: str,
                              target_dir: str) -> str:
    if branch != CURRENT_BRANCH:
        # user set branch for particular repo - print info, try download
        # artifact
        info('Getting artifact for plan {}\'s from branch {}'
             .format(plan, branch))
        exc_log = ('Branch {} in plan {} not found. Exiting...'
                   .format(branch, plan))
        res = download_artifact_safe(ssh=ssh,
                                     branch=branch,
                                     plan=plan,
                                     hostname=hostname,
                                     port=port,
                                     username=username,
                                     local_path=target_dir,
                                     exc_log=exc_log,
                                     exc_handler=sys.exit,
                                     exc_handler_pos_args=(1, ))
    else:
        # user didn't set particular branch - print info about branches,
        # try download artifact
        info('Trying to download artifact for plan {}\'s from branch {}. '
             'On failure artifact from {} branch will be downloaded.'
             .format(plan, current_branch, default_branch))

        res = download_specific_or_default(ssh=ssh,
                                           plan=plan,
                                           branch=current_branch,
                                           hostname=hostname,
                                           port=port,
                                           username=username,
                                           default_branch=default_branch,
                                           local_path=target_dir)
    return res


def get_artifact_info(artifact_path: str, branch: str = None) -> Dict:
    mtime = os.path.getmtime(artifact_path)
    parsed_mtime = (datetime.datetime
                    .fromtimestamp(mtime)
                    .strftime('%Y.%m.%d-%H.%M.%S'))
    return {'artifact-path': artifact_path,
            'modification-time': parsed_mtime,
            'branch': branch}


def get_source_info(path: str) -> Dict[str, str]:
    return {'path': path,
            'branch': get_git_branch_cmd(path)}


def check_if_source_is_present(plan: str) -> Tuple[bool, Dict[str, Any]]:
    if plan == 'onepanel':
        ozp_path, opp_path = get_onepanel_sources_locations()
        if any((ozp_path, opp_path)):
            info('Sources for oz-panel and op-panel was found in {} '
                 'and {} accordingly. Artifact won\'t be '
                 'downloaded'.format(ozp_path, opp_path))
            return True, {'oz-panel': get_source_info(ozp_path),
                          'op-panel': get_source_info(opp_path)}
    else:
        src_path = get_sources_location(plan, exit_on_error=False)
        if src_path:
            info('Sources for {} was found in {}. Artifact won\'t be '
                 'downloaded'.format(plan, src_path))
            return True, get_source_info(src_path)
    return False, {}


def get_artifact_path(artifact_name: str) -> Optional[str]:
    location, _ = find_files_in_relative_paths([artifact_name],
                                               ['../', '../../',
                                                LOCAL_ARTIFACTS_DIR])
    if not location:
        return None

    location = os.path.normpath(location)
    return location


def ensure_sources(branch_config: Dict[str, Any], ssh: SSHClient,
                   hostname: str, port: int,
                   username: str) -> Tuple[Dict[str, Any], Dict[str, str]]:
    sources_info = {}
    artifacts_to_unpack = {}

    if not os.path.exists(LOCAL_ARTIFACTS_DIR):
        os.makedirs(LOCAL_ARTIFACTS_DIR)

    for plan, branch in branch_config.get('branches').items():
        # check if sources for plan are present
        info('Trying to find sources for {}.'.format(plan))
        src_is_present, src_info = check_if_source_is_present(plan)
        if src_is_present:
            sources_info[plan] = src_info
        else:
            info('Sources for {} not found. Trying to find artifact.'
                 .format(plan))
            # check if artifact is present
            artifact_tar = artifact_tar_name(plan)
            artifact_path = get_artifact_path(artifact_tar)
            if artifact_path:
                info('Artifact for {} was found in {}.'
                     .format(plan, artifact_path))
                artifacts_to_unpack[plan] = artifact_path
                sources_info[plan] = get_artifact_info(artifact_path)
            else:
                # download missing artifact
                default_branch = branch_config.get(DEFAULT_BRANCH)
                current_branch = branch_config.get(CURRENT_BRANCH)
                downloaded_branch = download_missing_artifact(
                    plan=plan,
                    branch=branch,
                    ssh=ssh,
                    hostname=hostname,
                    port=port,
                    username=username,
                    default_branch=default_branch,
                    current_branch=current_branch,
                    target_dir=LOCAL_ARTIFACTS_DIR
                )
                if downloaded_branch:
                    artifact_path = os.path.join(LOCAL_ARTIFACTS_DIR,
                                                 artifact_tar)
                    artifacts_to_unpack[plan] = artifact_path
                    sources_info[plan] = get_artifact_info(artifact_path,
                                                           downloaded_branch)
        horizontal_line()
    return sources_info, artifacts_to_unpack


def s3_ensure_sources(branch_config: Dict[str, Any], s3_res: boto3.resource,
                      bucket: str) -> Tuple[Dict[str, Any], Dict[str, str]]:
    sources_info = {}
    artifacts_to_unpack = {}

    if not os.path.exists(LOCAL_ARTIFACTS_DIR):
        os.makedirs(LOCAL_ARTIFACTS_DIR)

    for plan, branch in branch_config.get('branches').items():
        # check if sources for plan are present
        info('Trying to find sources for {}.'.format(plan))
        src_is_present, src_info = check_if_source_is_present(plan)
        if src_is_present:
            sources_info[plan] = src_info
        else:
            info('Sources for {} not found. Trying to find artifact.'
                 .format(plan))
            # check if artifact is present
            artifact_tar = artifact_tar_name(plan)
            artifact_path = get_artifact_path(artifact_tar)
            if artifact_path:
                info('Artifact for {} was found in {}.'
                     .format(plan, artifact_path))
                artifacts_to_unpack[plan] = artifact_path
                sources_info[plan] = get_artifact_info(artifact_path)
            else:
                # download missing artifact
                default_branch = branch_config.get(DEFAULT_BRANCH)
                current_branch = branch_config.get(CURRENT_BRANCH)
                downloaded_branch = s3_download_missing_artifact(
                    s3_res=s3_res,
                    bucket=bucket,
                    plan=plan,
                    branch=branch,
                    default_branch=default_branch,
                    current_branch=current_branch,
                    target_dir=LOCAL_ARTIFACTS_DIR
                )
                if downloaded_branch:
                    artifact_path = os.path.join(LOCAL_ARTIFACTS_DIR,
                                                 artifact_tar)
                    artifacts_to_unpack[plan] = artifact_path
                    sources_info[plan] = get_artifact_info(artifact_path,
                                                           downloaded_branch)
        horizontal_line()
    return sources_info, artifacts_to_unpack


def extract_artifacts(artifacts_paths: Dict[str, str],
                      sources_info: Dict[str, Any]) -> Dict[str, Any]:
    for plan, artifact_path in artifacts_paths.items():
        info('Unpacking {}'.format(artifact_path))
        artifact_content = check_output(['tar', '--exclude=*/*',
                                         '-t', '-f', artifact_path])
        unpack_tar(artifact_path, LOCAL_ARTIFACTS_DIR)
        extracted_path = os.path.join(LOCAL_ARTIFACTS_DIR, artifact_content)
        if extracted_path:
            repo = get_git_repo(extracted_path)
            if repo == plan:
                branch = get_git_branch_cmd(extracted_path)
                sources_info[plan]['branch'] = branch
            sources_info[plan]['extracted_sources_path'] = extracted_path
        info('Done')
    return sources_info


def dump_sources_info(sources_info: Dict[str, Dict]):
    info_path = os.path.join(ONE_ENV_ROOT_DIR, 'sources_info.yaml')
    dump_yaml(sources_info, info_path)


def main() -> None:
    pull_artifacts_args_parser = argparse.ArgumentParser(
        prog='onenv pull_artifacts',
        formatter_class=arg_help_formatter.ArgumentsHelpFormatter,
        description='Pulls artifacts from repository. '
    )

    pull_artifacts_args_parser.add_argument(
        '-n', '--hostname',
        help='Hostname of artifacts repository',
        default=os.getenv(ARTIFACT_REPO_HOST_ENV)
    )

    pull_artifacts_args_parser.add_argument(
        '-p', '--port',
        type=int,
        help='SSH port to connect to',
        default=os.getenv(ARTIFACT_REPO_PORT_ENV)
    )

    pull_artifacts_args_parser.add_argument(
        '-u', '--username',
        help='The username to authenticate as',
        default='ubuntu'
    )

    pull_artifacts_args_parser.add_argument(
        '-b', '--branch',
        help='Name of branch for which artifacts should be downloaded. If '
             'branch does not exist in repository artifact from default '
             'branch will be used (by default its develop branch and can be '
             'configured through config file or --default-branch option).',
        default=get_current_branch()
    )

    pull_artifacts_args_parser.add_argument(
        '-d', '--default-branch',
        help='Name of default branch. When downloading artifact for branch '
             'specified with --branch option fails, script tries to download '
             'artifact from default branch.',
    )

    pull_artifacts_args_parser.add_argument(
        '--no-extract',
        action='store_false',
        help='Specifies if artifacts should be extracted after download. By '
             'default artifacts are extracted.',
        dest='extract'
    )

    # TODO: refactor after only s3_res repo will be used
    pull_artifacts_args_parser.add_argument(
        '--s3-url',
        help='The S3 endpoint URL',
        default='https://storage.cloud.cyfronet.pl'
    )

    pull_artifacts_args_parser.add_argument(
        '--s3-bucket',
        help='The S3 bucket name',
        default='bamboo-artifacts-2')

    pull_artifacts_args_parser.add_argument(
        nargs='?',
        help='Path to YAML file containing configuration of branches, from '
             'which artifacts should be downloaded. If not specified '
             'default branch config will be used. Command line arguments '
             'overrides file configuration.',
        dest='branch_config_path',
        default=branch_config_template_path()
    )

    pull_artifacts_args = pull_artifacts_args_parser.parse_args()

    hostname = pull_artifacts_args.hostname
    port = pull_artifacts_args.port
    username = pull_artifacts_args.username

    branch_config_path = pull_artifacts_args.branch_config_path
    branch = pull_artifacts_args.branch
    default_branch = pull_artifacts_args.default_branch

    branch_config = coalesce_branch_config(branch_config_path, branch,
                                           default_branch)

    if hostname != 'S3':
        if not hostname:
            error('Artifact repo hostname not provided. You can either set '
                  'env variable "{}" or set appropriate script argument.'
                  .format(ARTIFACT_REPO_HOST_ENV))
            sys.exit(1)

        if not port:
            error('Artifact repo port not provided. You can either set '
                  'env variable "{}" or set appropriate script argument.'
                  .format(ARTIFACT_REPO_PORT_ENV))
            sys.exit(1)

        ssh = ssh_to_artifact_repo(hostname, port, username)

        sources_info, artifacts_to_unpack = ensure_sources(branch_config, ssh,
                                                           hostname, port,
                                                           username)
        ssh.close()
    else:
        bucket = pull_artifacts_args.s3_bucket
        s3_res = get_s3_resource(pull_artifacts_args.s3_url)
        sources_info, artifacts_to_unpack = s3_ensure_sources(branch_config,
                                                              s3_res, bucket)

    if pull_artifacts_args.extract:
        sources_info = extract_artifacts(artifacts_to_unpack, sources_info)

    dump_sources_info(sources_info)


if __name__ == '__main__':
    main()
