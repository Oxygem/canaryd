import re

from canaryd.plugin import Plugin

from .mixins.service import ServiceMixin

UPSTART_REGEX = r'^([a-z\-]+) [a-z]+\/([a-z]+),?\s?(process)?\s?([0-9]+)?'


class Upstart(Plugin, ServiceMixin):
    spec = ('service', {
        'running': bool,
        'pid': int,
    })

    command = 'initctl list'

    @staticmethod
    def parse(output):
        services = {}

        for line in output.splitlines():
            matches = re.match(UPSTART_REGEX, line)
            if matches:
                pid = matches.group(4)

                if pid:
                    pid = int(pid)

                services[matches.group(1)] = {
                    'running': matches.group(2) == 'running',
                    'pid': pid,
                }

        return services
