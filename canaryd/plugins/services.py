import platform
import socket

from distutils.spawn import find_executable
from os import path

from canaryd.packages import six

from canaryd.plugin import Plugin

from .services_util import (
    get_initd_services,
    get_launchd_services,
    get_pid_to_ports,
    get_systemd_services,
    get_upstart_services,
)


def update_missing_keys(target, data):
    target.update(dict(
        (key, value)
        for key, value in six.iteritems(data)
        if key not in target
    ))


def check_port(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        result = sock.connect_ex(('127.0.0.1', port))
        return result == 0

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
                update_missing_keys(services, get_initd_services())

        # Get mapping of PID -> listening ports
        pid_to_ports = get_pid_to_ports()

        # Augment services with their ports
        for name, data in six.iteritems(services):
            if 'pid' not in data or data['pid'] not in pid_to_ports:
                continue

            data['ports'] = pid_to_ports[data['pid']]
            data['up_ports'] = [
                port for port in pid_to_ports[data['pid']]
                if check_port(port)
            ]

        return services
