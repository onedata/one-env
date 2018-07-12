"""
Part of onenv tool that allows to clean current onedata deployment.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import argparse

import helm
import user_config
import argparse_utils


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
# TODO: is this really needed?
# pods.clean_jobs()
# pods.clean_pods()

