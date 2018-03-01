from canaryd.packages import six

from canaryd.plugin import Plugin

# We ignore these because they constantly update and represent "live" state
# rather than configuration, which is what we're trying to track here.
IGNORE_PREFIXES = ('vm.', 'machdep.', 'debug.')


class Sysctl(Plugin):
    spec = ('key', {
        'values': [six.text_type],
    })

    command = (
        '(cat /etc/sysctl.conf || true); '
        '(cat /etc/sysctl.d/*.conf || true); '
        '(cat /run/sysctl.d/*.conf || true); '
        '(cat /usr/lib/sysctl.d/*.conf || true)'
    )

    def parse(self, output):
        state = {}

        for name, values in self.parse_lines(output.splitlines()):
            state[name] = {
                'values': values,
            }

        return state

    @staticmethod
    def parse_lines(lines):
        for line in lines:
            line = line.strip()

            if (
                line.startswith('#') or
                any(line.startswith(prefix) for prefix in IGNORE_PREFIXES)
            ):
                continue

            if ':' in line:
                bits = line.split()
                if len(bits) <= 1:
                    continue

                bits = [bits[0][:-1], bits[1]]

            else:
                bits = line.split('=')

            if len(bits) <= 1:
                continue

            name, value = bits
            name = name.strip()
            values = [v.strip() for v in value.split()]

            yield name, values
