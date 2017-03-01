from canaryd.plugin import Plugin

from .mixins.service import ServiceMixin

# We ignore these as they regularly get deleted/added as part of normal OSX
# lifecycle - and as such any events generated are not of use.
IGNORE_NAMES = ('oneshot', 'mdworker', 'mbfloagent')


class Launchctl(Plugin, ServiceMixin):
    spec = ('service', {
        'running': bool,
        'pid': int,
    })

    command = 'launchctl list'

    @staticmethod
    def parse(output):
        state = {}

        for line in output.splitlines():
            if any(name in line for name in IGNORE_NAMES):
                continue

            bits = line.split()

            if not bits or bits[0] == 'PID':
                continue

            name = bits[2]

            # If the last "bit" is just a number, it's the PID, so we strip it
            name_bits = name.split('.')
            if name_bits[-1].isdigit():
                name = '.'.join(name_bits[:-1])

            data = {}

            try:
                data['pid'] = int(bits[0])
            except ValueError:
                pass

            data['running'] = 'pid' in data

            state[name] = data

        return state
