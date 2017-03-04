import re

from canaryd.plugin import Plugin

from .mixins.service import ServiceMixin

SERVICE_REGEX = r'([a-zA-Z0-9\-]+)=([0-9]+)=([0-9]+)?'


class Initd(Plugin, ServiceMixin):
    spec = ('service', {
        'running': bool,
        'pid': int,
    })

    command = '''
        for SERVICE in `ls /etc/init.d/`; do
            _=`cat /etc/init.d/$SERVICE | grep status`
            if [ "$?" = "0" ]; then
                PID=` \
                    ps --ppid 1 -o 'tty,pid,comm' \
                    | grep ^?.*$SERVICE \
                    | head -n 1 \
                    | sed -n -e 's/?\s\+\([0-9]\+\)\s\+.*/\\1/p' \
                `
                STATUS=`/etc/init.d/$SERVICE status`
                echo "$SERVICE=$?=$PID"
            fi
        done
    '''

    @staticmethod
    def parse(output):
        services = {}

        for line in output.splitlines():
            matches = re.match(SERVICE_REGEX, line)
            if matches:
                status = int(matches.group(2))
                pid = matches.group(3)

                if pid:
                    pid = int(pid)

                # Exit code 0 = OK/running
                if status == 0:
                    status = True

                # Exit codes 1-3 = DOWN/not running
                elif status < 4:
                    status = False

                # Exit codes 4+ = unknown
                else:
                    status = None

                services[matches.group(1)] = {
                    'running': status or isinstance(pid, int),
                    'pid': pid,
                }

        return services
