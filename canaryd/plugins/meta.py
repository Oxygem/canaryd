import re
import socket

from datetime import datetime, timedelta

from canaryd.packages.check_output import check_output

from canaryd.plugin import Plugin

UPTIME_REGEX = re.compile((
    'up\s+(.*?),\s+([0-9]+) '
    'users?,\s+load averages?: '
    '([0-9]+\.[0-9][0-9]),?\s+([0-9]+\.[0-9][0-9]),?\s+([0-9]+\.[0-9][0-9])'
))


def ensure_datetime(datetime_or_string):
    if isinstance(datetime_or_string, datetime):
        return datetime_or_string

    return datetime.strptime(datetime_or_string, '%Y-%m-%dT%H:%M:%S')


def get_uptime_and_users():
    data = []
    output = check_output('uptime', shell=True)

    for line in output.splitlines():
        line = line.strip()
        matches = re.search(UPTIME_REGEX, line)

        if matches:
            duration, users, av1, av5, av15 = matches.groups()
            data.append(('users', int(users)))

            days = 0
            hours = 0
            mins = 0

            if 'day' in duration:
                match = re.search('([0-9]+)\s+day', duration)
                days = int(match.group(1))

            if ':' in duration:
                match = re.search('([0-9]+):([0-9]+)', duration)
                hours = int(match.group(1))
                mins = int(match.group(2))

            if 'min' in duration:
                match = re.search('([0-9]+)\s+min', duration)
                mins = int(match.group(1))

            up_since = datetime.utcnow() - timedelta(
                days=days, hours=hours, minutes=mins,
            )

            up_since = up_since.replace(
                second=0,
                microsecond=0,
            )

            data.append(('up_since', up_since))

    return data


def get_uname_data(flag):
    output = check_output(
        'uname -{0}'.format(flag),
        shell=True,
    )

    return output.strip()


class Meta(Plugin):
    spec = ('key', {
        'value': None,
    })

    @staticmethod
    def prepare(settings):
        pass

    @staticmethod
    def get_state(settings):
        data = get_uptime_and_users()
        data.append(('hostname', socket.gethostname()))
        data.append(('kernel', get_uname_data('s')))
        data.append(('kernel_release', get_uname_data('r')))
        data.append(('arch', get_uname_data('m')))

        # Nest each value in a dict
        return dict(
            (key, {
                'value': value,
            })
            for key, value in data
        )

    @staticmethod
    def is_change(key, previous_item, item):
        # Check to see if we rebooted, if not there's no change
        if key == 'up_since':
            previous_up = ensure_datetime(previous_item['value'])
            up = ensure_datetime(item['value'])

            if (
                previous_up.day == up.day
                and previous_up.hour == up.hour
                # Uptime is 1+ minutes less than previous
                and (previous_up.minute + 1) < up.minute
            ):
                return True
            else:
                return False

        # The # of active users shouldn't generate events!
        if key == 'users':
            return False

        return True

    @staticmethod
    def event_message(type_, key, data_changes):
        if type_ != 'updated':
            return

        if key == 'up_since':
            return 'Server rebooted'

        if key == 'hostname':
            return 'Hostname changed'
