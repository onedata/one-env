"""
Convenience functions for calling shell commands.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import subprocess
import os


def call(tokens):
    return subprocess.call(tokens)


def check_return_code(tokens):
    child = subprocess.Popen(tokens, stdout=open(os.devnull, 'w'),
                             stderr=subprocess.STDOUT)
    _ = child.communicate()[0]
    return child.returncode


def check_output(tokens):
    output = subprocess.check_output(tokens, stderr=open(os.devnull, 'w'))
    return output.decode('utf-8').strip()
