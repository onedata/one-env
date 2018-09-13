"""
Utils for os operations.
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"


import subprocess as sp

from pods import cmd_exec


def create_users(pod_name, users):
    """Creates system users on pod specified by 'pod'."""

    def _user_exists(user, pod_name):
        command = ['id', '-u', user]
        ret = sp.call(cmd_exec(pod_name, command))

        if ret == 1:
            return False
        elif ret == 0:
            return True

    for user in users:
        user_exists = _user_exists(user, pod_name)

        if user_exists:
            print('Skipping creation of user {} - user already exists in {}.'
                  .format(user, pod_name))
        else:
            uid = str(hash(user) % 50000 + 10000)
            command = ['adduser', '--disabled-password', '--gecos', '""',
                       '--uid', uid, user]
            assert 0 is sp.call(cmd_exec(pod_name, command))


def create_groups(pod_name, groups):
    """Creates system groups on docker specified by 'container'."""

    def _group_exists(group, pod_name):
        command = ['grep', '-q', group, '/etc/group']
        ret = sp.call(cmd_exec(pod_name, command))

        if ret == 1:
            return False
        elif ret == 0:
            return True

    for group in groups:
        group_exists = _group_exists(group, pod_name)
        if group_exists:
            print('Skipping creation of group {} - group already exists in {}.'
                  .format(group, pod_name))
        else:
            gid = str(hash(group) % 50000 + 10000)
            command = ['groupadd', '-g', gid, group]
            assert 0 is sp.call(cmd_exec(pod_name, command))
        for user in groups[group]:
            command = ['usermod', '-a', '-G', group, user]
            assert 0 is sp.call(cmd_exec(pod_name, command))
