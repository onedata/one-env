"""
Convenience functions that locate precompiled binaries to be used in env setup.
"""

__author__ = "Lukasz Opiola"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import os
import sys
import console


# app can be one of:
#   op-worker
#   oz-worker
#   op-panel
#   oz-panel
#   cluster-manager


def relative_binaries_path(app):
    return os.path.join('_build', 'default', 'rel',
                        app.replace('-', '_'))


def relative_start_script_path(app):
    return os.path.join(relative_binaries_path(app), 'bin',
                        app.replace('-', '_'))


def locate(app):
    app_underscores = app.replace('-', '_')
    app_dashes = app.replace('_', '-')
    cwd = os.getcwd()
    paths_to_check = [
        os.path.join(cwd, app_underscores),
        os.path.join(cwd, app_dashes),
        os.path.join(cwd, '../', app_underscores),
        os.path.join(cwd, '../', app_dashes)
    ]

    # FIXME hack
    if app_dashes == 'oz-panel' or app_dashes == 'op-panel':
        paths_to_check.extend([
            os.path.join(cwd, 'onepanel'),
            os.path.join(cwd, '../', 'onepanel')
        ])

    location = None
    for path in paths_to_check:
        if os.path.isdir(path):
            location = path

    if not location:
        console.error('Cannot locate directory for {}, tried:'.format(
            app))
        for path in paths_to_check:
            console.error('    ' + path)
        sys.exit(1)

    console.info('{} - using directory {}'.format(app, location))
    precompiled_binaries_location = os.path.join(location,
                                                 relative_binaries_path(app))
    if not os.path.isdir(precompiled_binaries_location):
        console.error(
            'Cannot locate precompiled binaries for {}, tried: {}'.format(
                app, precompiled_binaries_location))
        sys.exit(1)

    return location


def start_script_path(app, binaries):
    if binaries:
        return os.path.normpath(
            os.path.join(locate(app), relative_start_script_path(app)))
    else:
        return app.replace('-', '_')
