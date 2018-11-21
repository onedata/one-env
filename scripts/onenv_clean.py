"""
Part of onenv tool that allows to clean current onedata deployment.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import time
import argparse

from .utils import arg_help_formatter
from .utils.one_env_dir import user_config
from .utils.k8s import helm, pods


DEFAULT_RETRIES_NUM = 30


def clean_deployment() -> None:
    helm.clean_deployment()

    # without this onenv up can fail because of existing pvs
    pvs = pods.list_pvs()
    retries = DEFAULT_RETRIES_NUM

    while pvs and retries >= 0:
        pvs = pods.list_pvs()
        time.sleep(1)
        retries -= 1


def main() -> None:
    clean_args_parser = argparse.ArgumentParser(
        prog='onenv clean',
        formatter_class=arg_help_formatter.ArgumentsHelpFormatter,
        description='Cleans current onedata deployment.'
    )

    clean_args_parser.parse_args()

    user_config.ensure_exists()
    helm.ensure_deployment(exists=True, fail_with_error=False)

    clean_deployment()


if __name__ == '__main__':
    main()
