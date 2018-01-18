"""
Part of onenv tool that allows to clean current onedata deployment.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import argparse
import time
import sys
import pods

SCRIPT_DESCRIPTION = 'Cleans current onedata deployment.'

parser = argparse.ArgumentParser(
    prog='onenv clean',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    description=SCRIPT_DESCRIPTION
)

args = parser.parse_args()

print('hehe')