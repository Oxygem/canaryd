import re

from os import listdir, path, sep as os_sep

from canaryd.subprocess import CalledProcessError, get_command_output

# We ignore these as they regularly get deleted/added as part of normal OSX
# lifecycle - and as such any events generated are not of use.
LAUNCHCTL_IGNORE_NAMES = ('oneshot', 'mdworker', 'mbfloagent')

SYSTEMD_REGEX = r'^([a-z\-]+)\.service\s+[a-z\-]+\s+[a-z]+\s+([a-z]+)'
UPSTART_REGEX = r'^([a-z\-]+) [a-z]+\/([a-z]+),?\s?(process)?\s?([0-9]+)?'
SUPERVISOR_REGEX = r'([a-z\-]+)\s+([A-Z]+)\s+pid\s([0-9]+)'

INITD_REGEX = r'([a-zA-Z0-9\-]+)=([0-9]+)=([0-9]+)?'
INITD_USAGE_REGEX = re.compile(r'Usage:[^\n]+status')
IGNORE_INIT_SCRIPTS = []


def get_pid_to_listens():
    pid_to_ports = {}

    output = get_command_output(
        'netstat -plnt',
    )

    lines = output.splitlines()

    for line in lines[2:]:
        bits = line.split()
        proto, _, _, local_address, _, _, program = bits

        # Get the pid from PID/PROGRAM
        pid = program.split('/')[0]
        pid = int(pid)

        # Work out the host:port bit
        host, port = local_address.rsplit(':', 1)
        port = int(port)

        ip_type = 'ipv6' if proto == 'tcp6' else 'ipv4'

        pid_to_ports.setdefault(pid, set()).add((ip_type, host, port))

    return pid_to_ports


def get_launchd_services():
    '''
    Execute & parse ``launchctl list``.
    '''

    output = get_command_output(
        'launchctl list',
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
            script_data = script.read()

            if (
                # LSB header
                '### BEGIN INIT INFO' not in script_data
                or not INITD_USAGE_REGEX.search(script_data)
            ):
                IGNORE_INIT_SCRIPTS.append(name)
                continue

        # Get the status
        status = False

        try:
            get_command_output((script_path, 'status'))
            status = True

        except (OSError, CalledProcessError):
            pass

        # Get the PID
        pid = None
        pid_line = None

        try:
            pid_line = get_command_output(
                '''
                ps --ppid 1 -o 'tty,pid,comm' | \
                grep '^\?.*\s{0}.*$' | \
                head -n 1
                '''.format(name),
                shell=True,
            )
        except CalledProcessError:
            raise

        if pid_line:
            bits = pid_line.strip().split()
            try:
                pid = int(bits[-2])
            except (TypeError, ValueError):
                raise

        # Check if enabled
        enabled = False

        try:
            found_links = get_command_output(
                'find /etc/rc*.d/S*{0} -type l'.format(name),
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
    output = get_command_output(
        'systemctl -alt service list-units',
    )

    services = {}

    for line in output.splitlines():
        line = line.strip()
        matches = re.match(SYSTEMD_REGEX, line)
        if matches:
            name = matches.group(1)

            # Get service info to extract pid/enabled status
            service_output = get_command_output(
                'systemctl show {0}.service'.format(name),
            )

            service_meta = {}
            for line in service_output.splitlines():
                key, value = line.split('=', 1)
                service_meta[key] = value

            pid = service_meta.get(
                'ExecMainPID',
                service_meta.get('MainPID', None),
            )

            if pid:
                pid = int(pid)

            enabled = service_meta.get('UnitFileState') == 'enabled'

            services[name] = {
                'running': matches.group(2) == 'running',
                'pid': pid,
                'enabled': enabled,
                'init_system': 'systemd',
            }

    return services


def get_upstart_services():
    output = get_command_output(
        'initctl list',
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
    output = get_command_output(
        'supervisorctl status',
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
