from pods import cmd_exec, match_pods


def create_users(pod_name, users):
    """Creates system users on pod specified by 'pod'.
    """

    pod = match_pods(pod_name)[0]

    def _user_exists(user, pod):
        command = ['id', '-u', user]
        ret = cmd_exec(pod, command)

        if ret == 1:
            return False
        elif ret == 0:
            return True

    for user in users:
        user_exists = _user_exists(user, pod)

        if user_exists:
            print('Skipping creation of user {} - user already exists in {}.'
                  .format(user, pod))
        else:
            uid = str(hash(user) % 50000 + 10000)
            command = ["adduser", "--disabled-password", "--gecos", "''",
                       "--uid", uid, user]
            assert 0 is cmd_exec(pod, command)


def create_groups(pod_name, groups):
    """Creates system groups on docker specified by 'container'.
    """

    pod = match_pods(pod_name)[0]

    def _group_exists(group, pod):
        command = ['grep', '-q', group, '/etc/group']
        ret = cmd_exec(pod, command)

        if ret == 1:
            return False
        elif ret == 0:
            return True

    for group in groups:
        group_exists = _group_exists(group, pod)
        if group_exists:
            print('Skipping creation of group {} - group already exists in {}.'
                  .format(group, pod))
        else:
            gid = str(hash(group) % 50000 + 10000)
            command = ["groupadd", "-g", gid, group]
            assert 0 is cmd_exec(pod, command)
        for user in groups[group]:
            command = ["usermod", "-a", "-G", group, user]
            assert 0 is cmd_exec(pod, command)

