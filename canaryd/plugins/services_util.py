import re

from os import listdir, path, sep as os_sep

from subprocess import CalledProcessError

from canaryd.packages.check_output import check_output

# We ignore these as they regularly get deleted/added as part of normal OSX
# lifecycle - and as such any events generated are not of use.
LAUNCHCTL_IGNORE_NAMES = ('oneshot', 'mdworker', 'mbfloagent')

INITD_REGEX = r'([a-zA-Z0-9\-]+)=([0-9]+)=([0-9]+)?'
SYSTEMD_REGEX = r'^([a-z\-]+)\.service\s+[a-z\-]+\s+[a-z]+\s+([a-z]+)'
UPSTART_REGEX = r'^([a-z\-]+) [a-z]+\/([a-z]+),?\s?(process)?\s?([0-9]+)?'
SUPERVISOR_REGEX = r'([a-z\-]+)\s+([A-Z]+)\s+pid\s([0-9]+)'

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

        # Work out the host:port bit
        ip_host = bits[-2]
        host, port = ip_host.rsplit(':', 1)
        port = int(port)

        # Work out the IP type (4/6) by looking at the IP (contains : = ipv6)
        ip_type = 'ipv6' if ':' in host else 'ipv4'

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

        data = {
            'init_system': 'launchd',
        }

        try:
            data['pid'] = int(bits[0])
        except ValueError:
            pass

        data['running'] = 'pid' in data

        services[name] = data

    return services


def get_initd_services(existing_services=None):
    existing_services = existing_services or []

    init_dir = path.join(os_sep, 'etc', 'init.d')
    service_names = listdir(init_dir)
    services = {}

    for name in service_names:
        if name in existing_services or name in IGNORE_INIT_SCRIPTS:
            continue

        script_path = path.join(init_dir, name)

        with open(script_path) as script:
            if 'status' not in script.read():
                IGNORE_INIT_SCRIPTS.append(name)
                continue

        # Get the status
        status = False

        try:
            check_output((script_path, 'status'))
            status = True

        except (OSError, CalledProcessError):
            pass

        # Get the PID
        pid = None
        pid_line = None

        try:
            pid_line = check_output(
                '''
                ps --ppid 1 -o 'tty,pid,comm' | \
                grep '^\?.*\s{0}.*$' | \
                head -n 1
                '''.format(name),
                shell=True,
            )
        except CalledProcessError:
            pass

        if pid_line:
            bits = pid_line.strip().split()
            try:
                pid = int(bits[-2])
            except (TypeError, ValueError):
                pass

        # Check if enabled
        enabled = False

        try:
            found_links = check_output(
                'find /etc/rc*.d/S*{0} -type l'.format(name),
                shell=True,
            )

            if found_links.strip():
                enabled = True

        except CalledProcessError:
            pass

        services[name] = {
            'running': status or isinstance(pid, int),
            'pid': pid,
            'enabled': enabled,
            'init_system': 'initd',
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

            # Get service info to extract pid/enabled status
            service_output = check_output(
                'systemctl show {0}.service'.format(name),
                shell=True,
            )

            service_meta = {}
            for line in service_output.splitlines():
                key, value = line.split('=', 1)
                service_meta[key] = value

            # Skip/ignore Type=oneshot services
            if 'Type' in service_meta and service_meta['Type'] == 'oneshot':
                continue

            pid = service_meta.get(
                'ExecMainPID',
                service_meta.get('MainPID', None),
            )

            enabled = service_meta.get('UnitFileState') == 'enabled'

            services[name] = {
                'running': matches.group(2) == 'running',
                'pid': pid,
                'enabled': enabled,
                'init_system': 'systemd',
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
            name = matches.group(1)
            pid = matches.group(4)

            if pid:
                pid = int(pid)

            enabled = True

            # Check if enabled by looking in any override file
            override_filename = path.join(
                os_sep, 'etc', 'init',
                '{0}.override'.format(name),
            )
            if path.exists(override_filename):
                with open(override_filename) as script:
                    if 'manual' in script.read():
                        enabled = False

            services[name] = {
                'running': matches.group(2) == 'running',
                'pid': pid,
                'enabled': enabled,
                'init_system': 'upstart',
            }

    return services


def get_supervisor_services():
    output = check_output(
        'supervisorctl status',
        shell=True,
    )

    services = {}

    for line in output.splitlines():
        matches = re.match(SUPERVISOR_REGEX, line)

        if matches:
            name = matches.group(1)
            status = matches.group(2)
            pid = matches.group(3)

            services[name] = {
                'running': status == 'RUNNING',
                'pid': pid,
                'init_system': 'supervisor',
            }

    return services
