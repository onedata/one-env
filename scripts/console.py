"""
Convenience functions for pretty-printing output to the console.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

from termcolor import colored
import shutil
import sys


def info(s):
    print(colored('[INFO] ' + s, 'white'))


def warning(s):
    print(colored('[WARNING] ' + s, 'yellow'))


def error(s):
    print(colored('[ERROR] ' + s, 'red'))


def green_str(s):
    return colored(s, 'green')


def horizontal_line():
    (width, _) = shutil.get_terminal_size()
    print('-' * width)


def print_same_line(s):
    sys.stdout.write('{}\r'.format(s))
    sys.stdout.flush()
