"""
Part of onenv tool that allows to initialize ~/.one-env directory and
config files.
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2019 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import argparse

from .utils import arg_help_formatter
from .utils.one_env_dir import user_config


def main() -> None:
    init_args_parser = argparse.ArgumentParser(
        prog='onenv init',
        formatter_class=arg_help_formatter.ArgumentsHelpFormatter,
        description='Initialize ~/.one-env directory and config files'
    )

    init_args_parser.parse_args()
    user_config.ensure_exists()


if __name__ == '__main__':
    main()
