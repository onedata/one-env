"""
This module contains utilities for argparse module.
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import argparse


class ArgumentsHelpFormatter(argparse.HelpFormatter):
    """Help message formatter which adds default values to argument help.

    Only the name of this class is considered a public API. All the methods
    provided by the class are considered an implementation detail.
    """

    # pylint: disable=protected-access
    def _get_help_string(self, action: argparse.Action) -> str:
        help_msg = action.help
        if '%(default)' not in action.help:
            if (action.default not in (argparse.SUPPRESS, None) and
                    not isinstance(action, argparse._StoreTrueAction)):
                defaulting_nargs = [argparse.OPTIONAL, argparse.ZERO_OR_MORE]
                if action.option_strings or action.nargs in defaulting_nargs:
                    help_msg += ' (default: %(default)s)'
        return help_msg
