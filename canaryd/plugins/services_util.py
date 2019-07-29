import re

from collections import defaultdict
from os import listdir, path, sep as os_sep

from canaryd.log import logger
from canaryd.subprocess import CalledProcessError, get_command_output

# We ignore these as they regularly get deleted/added as part of normal OSX
# lifecycle - and as such any events generated are not of use.
LAUNCHCTL_IGNORE_NAMES = ('oneshot', 'mdworker', 'mbfloagent')

# Systemd service types to ignore
SYSTEMD_IGNORE_TYPES = ('oneshot',)
SYSTEMD_REGEX = re.compile(r'^([a-z\-]+)\.service\s+[a-z\-]+\s+[a-z]+\s+([a-z]+)')

UPSTART_REGEX = re.compile(r'^([a-z\-]+) [a-z]+\/([a-z]+),?\s?(process)?\s?([0-9]+)?')
SUPERVISOR_REGEX = re.compile(r'([a-z\-]+)\s+([A-Z]+)\s+pid\s([0-9]+)')

INITD_USAGE_REGEX = re.compile(r'Usage:[^\n]+status')
INITD_STATUS_REGEX = re.compile(r'\(pid\s+([0-9]+)\)')
# Known init scripts that either don't support status or don't handle it well/quickly
IGNORE_INIT_SCRIPTS = [
    'networking', 'udev-post', 'halt', 'killall',
    'kcare', 'vz',
]

# We *require* procfs to check PID -> port mappings
HAS_PROCFS = path.exists('/proc')
PID_TO_PORTS = defaultdict(set)


def _get_lsof_pid_to_listens(timeout):
    output = get_command_output(
        'lsof -i -n -P -b -l -L -s TCP:LISTEN',
        timeout=timeout,
    )

    for line in output.splitlines():
        # Skip bad/error lines
        if 'no pwd entry' in line:
            continue

        try:
            _, pid, _, _, ip_type, _, _, _, ip_host, _ = line.split(None, 9)

            ip_type = ip_type.lower()
            pid = int(pid)

            # Work out the host:port bit
            host, port = ip_host.rsplit(':', 1)
            port = int(port)

            host_port_tuple = (ip_type, host, port)
            PID_TO_PORTS[pid].add(host_port_tuple)
        except ValueError:
            logger.warning('Dodgy lsof line ignored: "{0}"'.format(line))


def _get_netstat_pid_to_listens(timeout):
    output = get_command_output(
        'netstat -plnt',
        timeout=timeout,
    )

    lines = output.splitlines()

    for line in lines[2:]:
        try:
            bits = line.split()
            proto, _, _, local_address, _, _, program = bits

            # Get the pid from PID/PROGRAM
            pid = program.split('/')[0]
            pid = int(pid)

            # Work out the host:port bit
            host, port = local_address.rsplit(':', 1)
            port = int(port)

            ip_type = 'ipv6' if proto == 'tcp6' else 'ipv4'

            host_port_tuple = (ip_type, host, port)
            PID_TO_PORTS[pid].add(host_port_tuple)
        except ValueError:
            logger.warning('Dodgy netstat line ignored: "{0}"'.format(line))


def get_pid_to_listens(timeout):
    if not HAS_PROCFS:
        return PID_TO_PORTS

    # Loop through the results and cleanup any PIDs that don't exist
    for pid in list(PID_TO_PORTS.keys()):
        if not path.exists('/proc/{0}'.format(pid)):
            PID_TO_PORTS.pop(pid)

    try:
        _get_lsof_pid_to_listens(timeout=timeout)
    except (CalledProcessError, OSError):
        logger.warning('Missing lsof, defaulting to netstat')

        try:
            _get_netstat_pid_to_listens(timeout=timeout)
        except (CalledProcessError, OSError):
            pass

    return PID_TO_PORTS


def get_launchd_services(timeout):
    '''
    Execute & parse ``launchctl list``.
    '''

    output = get_command_output(
        'launchctl list',
        timeout=timeout,
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


def get_initd_services(existing_services, timeout):
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
        pid = None

        try:
            status_line = get_command_output(
                (script_path, 'status'),
                timeout=timeout,
            )
            status = True

            matches = INITD_STATUS_REGEX.search(status_line)
            if matches:
                pid = int(matches.group(1))

        except (OSError, CalledProcessError):
            pass

        # Check if enabled
        enabled = False

        try:
            found_links = get_command_output(
                'find /etc/rc*.d/S*{0} -type l'.format(name),
                timeout=timeout,
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


def get_systemd_services(timeout):
    output = get_command_output(
        'systemctl -alt service list-units',
        timeout=timeout,
    )

    services = {}

    for line in output.splitlines():
        matches = SYSTEMD_REGEX.match(line.strip())
        if not matches:
            continue

        name = matches.group(1)

        # Get service info to extract pid/enabled status
        service_output = get_command_output(
            'systemctl show {0}.service'.format(name),
        )

        service_meta = {}
        for line in service_output.splitlines():
            key, value = line.split('=', 1)
            service_meta[key] = value

        if service_meta.get('Type') in SYSTEMD_IGNORE_TYPES:
            continue

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


def get_upstart_services(timeout):
    output = get_command_output(
        'initctl list',
        timeout=timeout,
    )

    services = {}

    for line in output.splitlines():
        matches = UPSTART_REGEX.match(line)
        if not matches:
            continue

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


def get_supervisor_services(timeout):
    output = get_command_output(
        'supervisorctl status',
        timeout=timeout,
    )

    services = {}

    for line in output.splitlines():
        matches = SUPERVISOR_REGEX.match(line)
        if not matches:
            continue

        name = matches.group(1)
        status = matches.group(2)
        pid = matches.group(3)

        services[name] = {
            'running': status == 'RUNNING',
            'pid': int(pid),
            'init_system': 'supervisor',
        }

    return services
