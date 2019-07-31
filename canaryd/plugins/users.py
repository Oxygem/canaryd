from canaryd_packages import six

from canaryd.log import logger
from canaryd.plugin import Plugin
from canaryd.subprocess import CalledProcessError, get_command_output

# Attempt to import pwd/grp - the users plugin is *nix only
try:
    import pwd
    import grp
except ImportError:
    pwd = None
    grp = None


def get_last_login_times(timeout):
    output = get_command_output(
        'lastlog',
        timeout=timeout,
    )

    user_logins = {}

    for line in output.splitlines()[1:]:
        user, _, ip, time = line.split(None, 3)
        if time.endswith('*'):
            continue

        user_logins[user] = {
            'login_time': time,
            'login_ip': ip,
        }

    return user_logins


class Users(Plugin):
    '''
    Tracks system users and groups, as well as login events.
    '''

    spec = ('user', {
        'group': six.text_type,
        'groups': [six.text_type],
        'home': six.text_type,
        'shell': six.text_type,
        'login_time': six.text_type,
        'login_ip': six.text_type,
    })

    def prepare(self, settings):
        if any(var is None for var in (pwd, grp)):
            raise self.PrepareError('Missing either pwd or group modules.')

    def get_state(self, settings):
        timeout = self.get_timeout(settings)

        try:
            user_logins = get_last_login_times(timeout)
        except (CalledProcessError, OSError) as e:
            logger.warning('Could not get last login times: {0}'.format(e))
            user_logins = {}

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
            data = {
                'groups': set(),
                'home': user.pw_dir,
                'shell': user.pw_shell,
            }

            username = user.pw_name

            if username in user_logins:
                data.update(user_logins[username])

            users[username] = data

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
                user_data['groups'] = sorted(list(user_data['groups']))

        return users

    @staticmethod
    def get_action_for_change(change):
        if change.type != 'updated':
            return

        if 'login_time' in change.data:
            return 'logged in'
