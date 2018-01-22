"""
Convenience functions for pretty-printing output to the console.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

from termcolor import colored


def info(s):
    print(colored('[INFO] ' + s, 'white'))


def warning(s):
    print(colored('[WARNING] ' + s, 'yellow'))


def error(s):
    print(colored('[ERROR] ' + s, 'red'))
