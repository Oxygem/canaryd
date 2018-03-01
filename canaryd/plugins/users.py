from canaryd.packages import six

from canaryd.plugin import Plugin

# Attempt to import pwd/grp - the users plugin is *nix only
try:
    import pwd
    import grp
except ImportError:
    pwd = None
    grp = None


class Users(Plugin):
    spec = ('user', {
        'group': six.text_type,
        'groups': [six.text_type],
        'home': six.text_type,
        'shell': six.text_type,
    })

    def prepare(self, settings):
        if any(var is None for var in (pwd, grp)):
            raise self.PrepareError('Missing either pwd or group modules.')

    def get_state(self, settings):
        users = {}

        # Get all groups and map by ID -> group
        groups_data = grp.getgrall()

        groups_by_id = dict(
            (group.gr_gid, group)
            for group in groups_data
        )

        # Get basic user data
        users_data = pwd.getpwall()

        for user in users_data:
            users[user.pw_name] = {
                'groups': set(),
                'home': user.pw_dir,
                'shell': user.pw_shell,
            }

            group = groups_by_id.get(user.pw_gid)
            if group:
                users[user.pw_name]['group'] = group.gr_name

        # Loop back through groups and apply any additional to users
        for group in groups_data:
            for username in group.gr_mem:
                if username not in users:
                    continue

                users[username]['groups'].add(group.gr_name)

        for user_data in six.itervalues(users):
            if 'groups' in user_data:
                user_data['groups'] = list(user_data['groups'])

        return users
