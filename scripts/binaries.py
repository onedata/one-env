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


def binaries_path(component):
    return os.path.join('_build', 'default', 'rel',
                        component.replace('-', '_'))


def locate(component):
    component_underscores = component.replace('-', '_')
    component_dashes = component.replace('_', '-')
    cwd = os.getcwd()
    paths_to_check = [
        os.path.join(cwd, component_underscores),
        os.path.join(cwd, component_dashes),
        os.path.join(cwd, '../', component_underscores),
        os.path.join(cwd, '../', component_dashes)
    ]
    location = None
    for path in paths_to_check:
        if os.path.isdir(path):
            location = path

    if not location:
        console.error('Cannot locate directory for {}, tried:'.format(
            component))
        for path in paths_to_check:
            console.error('    ' + path)
        sys.exit(1)

    console.info('{} - using directory {}'.format(component, location))
    precompile_binaries_location = os.path.join(location,
                                                binaries_path(component))
    if not os.path.isdir(precompile_binaries_location):
        console.error(
            'Cannot locate precompiled binaries for {}, tried: {}'.format(
                component, binaries_path(precompile_binaries_location)))
        sys.exit(1)

    return location
