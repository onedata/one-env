"""
Part of onenv tool that allows to exec to chosen pod in onedata deployment.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import argparse
import contextlib

from .utils import arg_help_formatter
from .utils.one_env_dir import user_config
from .utils.k8s import helm, pods


def main() -> None:
    exec_args_parser = argparse.ArgumentParser(
        prog='onenv exec',
        formatter_class=arg_help_formatter.ArgumentsHelpFormatter,
        description='Execs to chosen pod with an interactive shell.'
    )

    exec_args_parser.add_argument(
        nargs='?',
        help='pod name (or matching pattern, use "-" for wildcard)',
        dest='pod'
    )

    exec_args = exec_args_parser.parse_args()

    user_config.ensure_exists()
    helm.ensure_deployment(exists=True, fail_with_error=True)

    with contextlib.suppress(KeyboardInterrupt):
        pods.match_pod_and_run(exec_args.pod, pods.pod_exec)


if __name__ == '__main__':
    main()
