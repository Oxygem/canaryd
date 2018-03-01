import socket

from distutils.spawn import find_executable
from os import path, sep as os_sep

from canaryd.packages import six

from canaryd.plugin import Plugin
from canaryd.subprocess import CalledProcessError

from .services_util import (
    get_initd_services,
    get_launchd_services,
    get_pid_to_listens,
    get_supervisor_services,
    get_systemd_services,
    get_upstart_services,
)

COMMAND_TO_FUNC = {
    'launchctl': get_launchd_services,
    'systemctl': get_systemd_services,
    'initctl': get_upstart_services,

    'supervisorctl': get_supervisor_services,
}


def check_port(ip_type, host, port):
    # Open our IPv4 or IPv6 socket
    socket_type = socket.AF_INET if ip_type == 'ipv4' else socket.AF_INET6
    sock = socket.socket(socket_type, socket.SOCK_STREAM)
    sock.settimeout(1)

    # If listening everywhere, just try localhost
    if host == '*':
        if ip_type == 'ipv4':
            host = '127.0.0.1'
        else:
            host = '::1'

    try:
        result = sock.connect_ex((host, port))
        return result == 0

    except (socket.error, socket.gaierror):
        pass

    finally:
        sock.close()


def make_service_data(data):
    blank_service = {
        'ports': [],
        'up_ports': [],
    }

    blank_service.update(data)
    return blank_service


class Services(Plugin):
    '''
    The services plugin provides a combined view of "system" services - ie the
    merge of any running launchctl/rcd/initd/upstart/systemd services.
    '''

    spec = ('service', {
        'running': bool,
        'pid': int,
        'enabled': bool,
        'init_system': six.text_type,
        'ports': [int],
        'up_ports': [int],
    })

    @staticmethod
    def prepare(settings):
        commands = COMMAND_TO_FUNC.keys()

        if not path.exists(path.join(os_sep, 'etc', 'init.d')) and not any(
            find_executable(command)
            for command in commands
        ):
            raise OSError('No container commands found: {0}'.format(commands))

    @staticmethod
    def get_state(settings):
        services = {}

        for command, func in six.iteritems(COMMAND_TO_FUNC):
            if find_executable(command):
                services.update(func())

        if path.exists(path.join(os_sep, 'etc', 'init.d')):
            services.update(
                # Pass existing services to avoid overhead of running all the
                # init.d status scripts.
                get_initd_services(existing_services=services),
            )

        # Get mapping of PID -> listening ports
        try:
            pid_to_listens = get_pid_to_listens()

        except (CalledProcessError, OSError):
            pass

        else:
            # Augment services with their ports
            for name, data in six.iteritems(services):
                if 'pid' not in data or data['pid'] not in pid_to_listens:
                    data['ports'] = set()
                    data['up_ports'] = set()
                    continue

                data['ports'] = set(
                    port
                    for _, _, port in pid_to_listens[data['pid']]
                )

                data['up_ports'] = set(
                    port for ip_type, host, port in pid_to_listens[data['pid']]
                    if check_port(ip_type, host, port)
                )

        return services

    @staticmethod
    def generate_events(type_, key, data_changes, settings):
        # For new services, no events
        if type_ == 'added':
            return

        # If the script has been removed, resolve any leftover issues and exit
        # (the delete event is still created).
        if type_ == 'deleted':
            yield 'resolved', None, None
            return

        # Track if the service starts/stops
        if 'running' in data_changes:
            _, to_running = data_changes['running']

            if to_running:
                yield 'updated', '{0} started'.format(key), data_changes

            else:
                yield 'updated', '{0} stopped'.format(key), data_changes
                # We stopped the service - so it's ports being up is no longer
                # an issue.
                return

        # No up/down change but PID changed? Service restarted!
        elif 'pid' in data_changes:
            yield 'updated', '{0} restarted'.format(key), data_changes

        # Finally, check the ports!
        if 'up_ports' in data_changes:
            from_ports, to_ports = data_changes['up_ports']

            # No ports up now?
            if from_ports and not to_ports:
                if settings.service_critical:
                    yield (
                        'critical',
                        'All {0} ports down'.format(key),
                        data_changes,
                    )

            # We lost 1+ port, but not all?
            elif from_ports and len(to_ports) < len(from_ports):
                if settings.service_warning:
                    yield (
                        'warning',
                        'Some {0} ports down'.format(key),
                        data_changes,
                    )

            # We have more ports than before? Assume resolved
            # TODO: improve this
            elif to_ports:
                yield 'resolved', 'All {0} ports up'.format(key), data_changes
