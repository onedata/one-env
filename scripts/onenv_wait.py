"""
Part of onenv tool that allows to wait for a deployment to be ready.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import sys
import time
import argparse
import contextlib

from .utils import terminal
from .utils.one_env_dir import user_config
from .utils.k8s import helm, pods


def wait(timeout: int) -> None:
    start_time = time.time()

    with contextlib.suppress(KeyboardInterrupt):
        while int(time.time() - start_time) <= timeout:
            if pods.all_jobs_succeeded() and pods.all_pods_running():
                sys.exit(0)
            else:
                time.sleep(0.5)
        terminal.error('Deployment failed to initialize within {} '
                       'seconds'.format(timeout))
        sys.exit(1)


def main() -> None:
    wait_args_parser = argparse.ArgumentParser(
        prog='onenv wait',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description='Waits for current deployment to be ready.'
    )

    wait_args_parser.add_argument(
        '-t', '--timeout',
        default=300,
        type=int,
        help='timeout (in seconds) after which the script terminates '
             'with failure'
    )

    wait_args = wait_args_parser.parse_args()

    user_config.ensure_exists()
    helm.ensure_deployment(exists=True, fail_with_error=True)

    wait(wait_args.timeout)


if __name__ == '__main__':
    main()
