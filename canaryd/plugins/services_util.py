import re

from subprocess import CalledProcessError

from canaryd.packages.check_output import check_output

# We ignore these as they regularly get deleted/added as part of normal OSX
# lifecycle - and as such any events generated are not of use.
LAUNCHCTL_IGNORE_NAMES = ('oneshot', 'mdworker', 'mbfloagent')

INITD_REGEX = r'([a-zA-Z0-9\-]+)=([0-9]+)=([0-9]+)?'
SYSTEMD_REGEX = r'^([a-z\-]+)\.service\s+[a-z\-]+\s+[a-z]+\s+([a-z]+)'
UPSTART_REGEX = r'^([a-z\-]+) [a-z]+\/([a-z]+),?\s?(process)?\s?([0-9]+)?'


def get_pid_to_listens():
    output = check_output(
        'lsof -i -n -P -s TCP:LISTEN',
        shell=True,
    )

    pid_to_ports = {}

    for line in output.splitlines():
        bits = line.split()

        if bits[-1] != '(LISTEN)':
            continue

        pid = int(bits[1])

        # Get the type of IP (4/6)
        ip_type = bits[4].lower()

        # Work out the host:port bit
        ip_host = bits[-2]
        host, port = ip_host.rsplit(':', 1)
        port = int(port)

        pid_to_ports.setdefault(pid, set()).add((ip_type, host, port))

    return pid_to_ports


def get_launchd_services():
    '''
    Execute & parse ``launchctl list``.
    '''

    output = check_output(
        'launchctl list',
        shell=True,
    )

    services = {}

    for line in output.splitlines():
        if any(name in line for name in LAUNCHCTL_IGNORE_NAMES):
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

        services[name] = data

    return services


def get_initd_services():
    output = check_output('''
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
    ''', shell=True)

    services = {}

    for line in output.splitlines():
        matches = re.match(INITD_REGEX, line)
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


def get_systemd_services():
    output = get_systemd_services(
        'systemctl -alt service list-units',
        shell=True,
    )

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


def get_upstart_services():
    output = check_output(
        'initctl list',
        shell=True,
    )

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
