import re
import socket

from datetime import datetime, timedelta

from canaryd.plugin import Plugin
from canaryd.subprocess import get_command_output

UPTIME_REGEX = re.compile((
    r'up\s+(.*?),\s+[0-9]+ '
    r'users?,\s+load averages?: '
    r'([0-9]+\.[0-9][0-9]),?\s+([0-9]+\.[0-9][0-9]),?\s+([0-9]+\.[0-9][0-9])'
))


def ensure_datetime(datetime_or_string):
    if isinstance(datetime_or_string, datetime):
        return datetime_or_string

    return datetime.strptime(datetime_or_string, '%Y-%m-%dT%H:%M:%S')


def get_uptime():
    data = []
    output = get_command_output('uptime')

    for line in output.splitlines():
        line = line.strip()
        matches = re.search(UPTIME_REGEX, line)

        if matches:
            duration, av1, av5, av15 = matches.groups()

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
    output = get_command_output(
        'uname -{0}'.format(flag),
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
        data = get_uptime()
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
    def should_apply_change(change):
        # Check to see if we rebooted, if not there's no change
        if change.key == 'up_since':
            old_up, new_up = change.data['value']

            previous_up = ensure_datetime(old_up)
            # Account for slight jitter
            previous_up += timedelta(minutes=1)

            up = ensure_datetime(new_up)

            if (previous_up < up):
                return True
            else:
                return False

        return True

    @staticmethod
    def get_description_for_change(change):
        if change.type != 'updated':
            return

        if change.key == 'up_since':
            return 'Server rebooted'
