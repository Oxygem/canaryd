import re

from os import listdir

from subprocess import CalledProcessError

from canaryd.packages.check_output import check_output

# We ignore these as they regularly get deleted/added as part of normal OSX
# lifecycle - and as such any events generated are not of use.
LAUNCHCTL_IGNORE_NAMES = ('oneshot', 'mdworker', 'mbfloagent')

INITD_REGEX = r'([a-zA-Z0-9\-]+)=([0-9]+)=([0-9]+)?'
SYSTEMD_REGEX = r'^([a-z\-]+)\.service\s+[a-z\-]+\s+[a-z]+\s+([a-z]+)'
UPSTART_REGEX = r'^([a-z\-]+) [a-z]+\/([a-z]+),?\s?(process)?\s?([0-9]+)?'

IGNORE_INIT_SCRIPTS = []


def get_pid_to_listens():
    output = check_output(
        'lsof -i -n -P -s TCP:LISTEN',
        shell=True,
    )

    pid_to_ports = {}

    for line in output.splitlines():
        bits = line.split()

        if len(bits) < 5 or bits[-1] != '(LISTEN)':
            continue

        try:
            pid = int(bits[1])
        except (TypeError, ValueError):
            continue

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


def get_initd_services(existing_services=None):
    existing_services = existing_services or []

    service_names = listdir('/etc/init.d/')
    services = {}

    for name in service_names:
        if name in existing_services or name in IGNORE_INIT_SCRIPTS:
            continue

        with open('/etc/init.d/{0}'.format(name)) as script:
            if 'status' not in script.read():
                IGNORE_INIT_SCRIPTS.append(name)
                continue

        status = False

        try:
            check_output(
                'grep /etc//etc/init.d/{0} status'.format(name),
                shell=True,
            )

            status = True

        except CalledProcessError:
            pass

        pid = None

        try:
            pid_line = check_output(
                "ps --ppid 1 -o 'tty,pid,comm' | grep '^?.*\s{0}.*$'".format(name),
                shell=True,
            )

            bits = pid_line.strip().split()

            try:
                pid = int(bits[-2])
            except (TypeError, ValueError):
                pass

        except CalledProcessError:
            pass

        services[name] = {
            'running': status or isinstance(pid, int),
            'pid': pid,
        }

    return services


def get_systemd_services():
    output = check_output(
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
