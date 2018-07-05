"""
Part of onenv tool that allows to wait for a deployment to be ready.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import argparse
import time
import sys
import pods
import helm
import console
import user_config

SCRIPT_DESCRIPTION = 'Waits for current deployment to be ready.'

parser = argparse.ArgumentParser(
    prog='onenv wait',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    description=SCRIPT_DESCRIPTION
)

parser.add_argument(
    '-t', '--timeout',
    action='store',
    default=300,
    help='timeout (in seconds) after which the script terminates with failure',
    dest='timeout')

user_config.ensure_exists()
helm.ensure_deployment(exists=True, fail_with_error=True)

args = parser.parse_args()

start_time = time.time()


try:
    while int(time.time() - start_time) <= int(args.timeout):
        if pods.all_jobs_succeeded() and pods.all_pods_running()::
            sys.exit(0)
        else:
            time.sleep(0.5)

    console.error('Deployment failed to initialize within {} seconds'.format(
        args.timeout
    ))
    sys.exit(1)
except KeyboardInterrupt:
    pass
