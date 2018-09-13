"""
Part of onenv tool that allows to clean current onedata deployment.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import time
import argparse

import helm
import pods
import user_config
import argparse_utils


DEFAULT_TIMEOUT = 30
SCRIPT_DESCRIPTION = 'Cleans current onedata deployment.'

parser = argparse.ArgumentParser(
    prog='onenv clean',
    formatter_class=argparse_utils.ArgumentsHelpFormatter,
    description=SCRIPT_DESCRIPTION
)


args = parser.parse_args()

user_config.ensure_exists()
helm.ensure_deployment(exists=True, fail_with_error=False)

helm.clean_deployment()

# without this onenv up can fail because of existing pvs
pvs = pods.list_pvs()
timeout = DEFAULT_TIMEOUT

while pvs and timeout >= 0:
    pvs = pods.list_pvs()
    print(pvs)
    time.sleep(1)
    timeout -= 1

# TODO: is this really needed?
# pods.clean_persistent_volumes()
