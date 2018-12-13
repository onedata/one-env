"""
Convenience functions for calling shell commands.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import subprocess
from typing import List, Union, IO, Any


File = Union[None, int, IO[Any]]


def call(tokens: List[str]) -> int:
    return subprocess.call(tokens)


def check_return_code(tokens: List[str],
                      stdout: File = subprocess.DEVNULL,
                      stderr: File = subprocess.STDOUT,
                      shell: bool = False) -> int:
    child = subprocess.Popen(tokens, stdout=stdout, stderr=stderr,
                             shell=shell)
    return child.wait()


def check_output(tokens: List[str],
                 stderr: File = subprocess.DEVNULL) -> str:
    output = subprocess.check_output(tokens, stderr=stderr)
    return output.decode('utf-8').strip()
