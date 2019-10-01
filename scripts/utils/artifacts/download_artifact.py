"""
This module contains utilities functions for artifacts management.
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2019 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import os
import sys
import signal
from typing import Optional, Callable, Any, Tuple, Dict

import boto3
import botocore.exceptions
from scp import SCPClient, SCPException
from paramiko import SSHClient, SSHException

from . import ARTIFACTS_EXT, REPO_ARTIFACTS_DIR
from ..terminal import info, error


def print_error_and_exit(plan):
    error('Could not get artifact for plan {}.'.format(plan))
    sys.exit(1)


def download_specific_or_default(*, ssh: SSHClient, plan: str, branch: str,
                                 hostname: str, port: int, username: str,
                                 default_branch: str,
                                 local_path: str) -> str:
    exc_log = ('Artifact of plan {}, specific for branch {} not found, '
               'pulling artifact from branch {}.'.format(plan, branch,
                                                         default_branch))
    return download_artifact_safe(ssh=ssh,
                                  plan=plan,
                                  branch=branch,
                                  hostname=hostname,
                                  port=port,
                                  username=username,
                                  local_path=local_path,
                                  exc_handler=download_default_artifact,
                                  exc_handler_kw_args={'ssh': ssh,
                                                       'plan': plan,
                                                       'branch': default_branch,
                                                       'hostname': hostname,
                                                       'port': port,
                                                       'username': username,
                                                       'local_path': local_path},
                                  exc_log=exc_log)


def s3_download_specific_or_default(*, s3_res: boto3.resource, bucket: str,
                                    plan: str, branch: str,
                                    default_branch: str,
                                    local_path: str) -> str:
    exc_log = ('Artifact of plan {}, specific for branch {} not found, '
               'pulling artifact from branch {}.'.format(plan, branch,
                                                         default_branch))
    exc_handler_kw_args = {'s3_res': s3_res,
                           'bucket': bucket,
                           'plan': plan,
                           'branch': default_branch,
                           'local_path': local_path}

    return s3_download_artifact_safe(s3_res=s3_res,
                                     bucket=bucket,
                                     plan=plan,
                                     branch=branch,
                                     local_path=local_path,
                                     exc_handler=s3_download_default_artifact,
                                     exc_handler_kw_args=exc_handler_kw_args,
                                     exc_log=exc_log)


def download_default_artifact(*, ssh: SSHClient, plan: str, branch: str,
                              hostname: str, port: int, username: str,
                              local_path: str) -> str:
    exc_log = ('Pulling artifact of plan {}, from branch {} failed. Exiting...'
               .format(plan, branch))
    return download_artifact_safe(ssh=ssh,
                                  plan=plan,
                                  branch=branch,
                                  hostname=hostname,
                                  port=port,
                                  username=username,
                                  local_path=local_path,
                                  exc_log=exc_log,
                                  exc_handler=print_error_and_exit,
                                  exc_handler_pos_args=(plan,))


def s3_download_default_artifact(*, s3_res: boto3.resource, bucket: str,
                                 plan: str, branch: str,
                                 local_path: str) -> str:
    exc_log = ('Pulling artifact of plan {}, from branch {} failed. Exiting...'
               .format(plan, branch))
    return s3_download_artifact_safe(s3_res=s3_res,
                                     bucket=bucket,
                                     plan=plan,
                                     branch=branch,
                                     local_path=local_path,
                                     exc_log=exc_log,
                                     exc_handler=print_error_and_exit,
                                     exc_handler_pos_args=(plan,))


def download_artifact_safe(*, ssh: SSHClient, plan: str, branch: str,
                           hostname: str, port: int, username: str,
                           local_path: str,
                           exc_handler: Optional[Callable[..., Any]] = None,
                           exc_handler_pos_args: Tuple[Any, ...] = (),
                           exc_handler_kw_args: Optional[Dict[str, Any]] = None,
                           exc_log: str = '') -> Optional[str]:
    def signal_handler(_signum, _frame):
        ssh.connect(hostname, port=port, username=username)
        sys.exit(1)

    signal.signal(signal.SIGINT, signal_handler)

    try:
        download_artifact(ssh, plan, branch, local_path)
        return branch
    except (SCPException, SSHException) as ex:
        info('{}.\nFailure reason: {}'.format(exc_log, ex))
        if exc_handler:
            return (exc_handler(*exc_handler_pos_args)
                    if exc_handler_kw_args is None
                    else exc_handler(*exc_handler_pos_args,
                                     **exc_handler_kw_args))
        return None


def s3_download_artifact_safe(*, s3_res: boto3.resource, bucket: str, plan: str,
                              branch: str, local_path: str,
                              exc_handler: Optional[Callable[..., Any]] = None,
                              exc_handler_pos_args: Tuple[Any, ...] = (),
                              exc_handler_kw_args: Optional[Dict[str, Any]] = None,
                              exc_log: str = '') -> Optional[str]:
    try:
        s3_download_artifact(s3_res, bucket, plan, branch, local_path)
        return branch
    except botocore.exceptions.BotoCoreError as ex:
        info('{}.\nFailure reason: {}'.format(exc_log, ex))
        if exc_handler:
            return (exc_handler(*exc_handler_pos_args)
                    if exc_handler_kw_args is None
                    else exc_handler(*exc_handler_pos_args,
                                     **exc_handler_kw_args))
        return None


def download_artifact(ssh: SSHClient, plan: str, branch: str,
                      local_path: str) -> None:
    artifact_tar = artifact_tar_name(plan)
    with SCPClient(ssh.get_transport()) as scp:
        scp.get(artifact_path(plan, branch),
                local_path=os.path.join(local_path, artifact_tar),
                preserve_times=True)


def s3_download_artifact(s3_res: boto3.resource, bucket: str, plan: str,
                         branch: str, local_path: str) -> None:
    bucket = s3_res.Bucket(bucket)
    artifact_tar = artifact_tar_name(plan)
    bucket.download_file(artifact_path(plan, branch),
                         os.path.join(local_path, artifact_tar))


def artifact_path(plan: str, branch: str) -> str:
    return os.path.join(REPO_ARTIFACTS_DIR, plan, branch + ARTIFACTS_EXT)


def artifact_tar_name(plan: str) -> str:
    return plan.replace('-', '_') + ARTIFACTS_EXT
