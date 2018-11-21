"""
Convenience functions for calling shell commands.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import subprocess
from typing import List, Union, IO, Any


def call(tokens: List[str]) -> int:
    return subprocess.call(tokens)


def check_return_code(tokens: List[str]) -> int:
    child = subprocess.Popen(tokens, stdout=subprocess.DEVNULL,
                             stderr=subprocess.STDOUT)
    return child.wait()


def check_output(tokens: List[str],
                 stderr: Union[None, int, IO[Any]] = subprocess.DEVNULL) -> str:
    output = subprocess.check_output(tokens, stderr=stderr)
    return output.decode('utf-8').strip()
