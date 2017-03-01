import re

from subprocess import CalledProcessError

from canaryd.packages.check_output import check_output

from canaryd.plugin import Plugin

from .mixins.service import ServiceMixin

SYSTEMD_REGEX = r'^([a-z\-]+)\.service\s+[a-z\-]+\s+[a-z]+\s+([a-z]+)'


class Systemd(Plugin, ServiceMixin):
    spec = ('service', {
        'running': bool,
        'pid': int,
    })

    command = 'systemctl -alt service list-units'

    @staticmethod
    def parse(output):
        services = {}

        for line in output.splitlines():
            line = line.strip()
            matches = re.match(SYSTEMD_REGEX, line)
            if matches:
                name = matches.group(1)

                pid = None

                try:
                    pid = check_output(
                        'systemctl status {0}.service | grep "Main PID:"'.format(name),
                        shell=True,
                    )
                    pid = pid.split()

                    for bit in pid:
                        try:
                            pid = int(bit)
                            break
                        except ValueError:
                            pass

                except (CalledProcessError, OSError):
                    pass

                services[name] = {
                    'running': matches.group(2) == 'running',
                    'pid': pid,
                }

        return services
