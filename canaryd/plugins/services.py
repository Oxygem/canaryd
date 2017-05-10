import platform
import socket

from distutils.spawn import find_executable
from os import path

from canaryd.packages import six

from canaryd.plugin import Plugin

from .services_util import (
    get_initd_services,
    get_launchd_services,
    get_pid_to_listens,
    get_systemd_services,
    get_upstart_services,
)


def update_missing_keys(target, data):
    target.update(dict(
        (key, value)
        for key, value in six.iteritems(data)
        if key not in target
    ))


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


class Services(Plugin):
    '''
    The services plugin provides a combined view of "system" services - ie the
    merge of any running launchctl/rcd/initd/upstart/systemd services.
    '''

    spec = ('service', {
        'running': bool,
        'pid': int,
        'init_system': six.text_type,
        'ports': set((int,)),
        'up_ports': set((int,)),
    })

    @staticmethod
    def prepare(settings):
        pass

    def get_state(self, settings):
        services = {}

        os_type = platform.system().lower()

        if os_type == 'darwin':
            services = get_launchd_services()

        elif os_type == 'linux':
            if find_executable('systemctl'):
                update_missing_keys(services, get_systemd_services())

            if find_executable('initctl'):
                update_missing_keys(services, get_upstart_services())

            if path.exists('/etc/init.d'):
                update_missing_keys(
                    services,
                    get_initd_services(existing_services=services),
                )

        # Get mapping of PID -> listening ports
        pid_to_listens = get_pid_to_listens()

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
            else:
                yield 'resolved', 'All {0} ports up'.format(key), data_changes
