"""
Part of onenv tool that allows to clean current onedata deployment.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import time
import argparse

from .utils.k8s import helm, pods
from .utils import shell, terminal
from .utils import arg_help_formatter
from .utils.one_env_dir import user_config
from .utils.one_env_dir import deployment_data


DEFAULT_RETRIES_NUM = 30


def clean_deployment(all_deployments: bool = False,
                     persistent_volumes: bool = False) -> None:
    if all_deployments:
        try:
            releases = deployment_data.get(default={}).get('releases', {})
        except FileNotFoundError as err:
            terminal.warning('Could not find: {}. Will delete only default '
                             'deployment.'.format(err.filename))
            helm.clean_release()
        else:
            for release in releases:
                helm.clean_release(release)
            # ensure default deployment is deleted
            # useful in case of k8s errors on bamboo
            helm.clean_release()
    else:
        helm.clean_release()

    if persistent_volumes:
        pvs = pods.list_pvs()
        retries = DEFAULT_RETRIES_NUM

        while pvs and retries >= 0:
            shell.call(pods.delete_kube_object_cmd('pv'))
            pvs = pods.list_pvs()
            time.sleep(1)
            retries -= 1


def main() -> None:
    clean_args_parser = argparse.ArgumentParser(
        prog='onenv clean',
        formatter_class=arg_help_formatter.ArgumentsHelpFormatter,
        description='Cleans current onedata deployment.'
    )

    clean_args_parser.add_argument(
        '-a', '--all',
        action='store_true',
        help='deletes all helm deployments registered in deployment data. '
             'This is useful when oneclient deployments have been started '
             'using oneclient command.'
    )

    clean_args_parser.add_argument(
        '-v', '--persistent-volumes',
        action='store_true',
        help='forces removing all persistent volumes. This is useful when '
             'some nfs volumes exists from previous deployments. Be careful: '
             'this option deletes all persistent volumes in current '
             'namespace, regardless of helm deployment in which they were '
             '-started.',
        dest='persistent_volumes'
    )

    clean_args = clean_args_parser.parse_args()

    user_config.ensure_exists()
    helm.ensure_deployment(exists=True, fail_with_error=False)

    clean_deployment(clean_args.all, clean_args.persistent_volumes)


if __name__ == '__main__':
    main()
