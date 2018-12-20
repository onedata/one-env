"""
Convenience functions for pretty-printing output to the console.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import shutil

from termcolor import colored


def info(msg: str) -> None:
    print(colored('[INFO] ' + msg, 'white'), flush=True)


def warning(msg: str) -> None:
    print(colored('[WARNING] ' + msg, 'yellow'), flush=True)


def error(msg: str) -> None:
    print(colored('[ERROR] ' + msg, 'red'), flush=True)


def green_str(msg: str) -> str:
    return colored(msg, 'green')


def red_str(msg: str) -> str:
    return colored(msg, 'red')


def horizontal_line() -> None:
    width, _ = shutil.get_terminal_size()
    print('-' * width, flush=True)


def print_same_line(line: str) -> None:
    print(line, end='\r', flush=True)
