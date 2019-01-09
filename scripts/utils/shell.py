"""
Convenience functions for calling shell commands.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import subprocess as sp
from typing import List, Union, IO, Any


from .terminal import error

File = Union[None, int, IO[Any]]


def call(tokens: List[str]) -> int:
    return sp.call(tokens)


def get_return_code(tokens: List[str], stdout: File = sp.DEVNULL,
                    stderr: File = sp.DEVNULL, shell: bool = False) -> int:
    child = sp.Popen(tokens, stdout=stdout, stderr=stderr, shell=shell)
    return child.wait()


def check_output(tokens: List[str],
                 stderr: File = sp.DEVNULL) -> str:
    output = sp.check_output(tokens, stderr=stderr)
    return output.decode('utf-8').strip()


def call_and_check_return_code(tokens: List[str], stdout: File = sp.DEVNULL,
                               stderr: File = sp.STDOUT,
                               shell: bool = False) -> None:
    ret = get_return_code(tokens, stdout=stdout, stderr=stderr, shell=shell)
    if ret != 0:
        error('Error in command: "{}". More information in logs '
              'file.'.format(' '.join(tokens)))
