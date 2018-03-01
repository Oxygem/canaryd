from distutils.spawn import find_executable

from canaryd.packages import six

from canaryd.plugin import Plugin

from .containers_util import (
    get_docker_containers,
    get_lxc_containers,
    get_openvz_containers,
    get_virsh_containers,
)

COMMAND_TO_FUNC = {
    'docker': get_docker_containers,
    'lxc': get_lxc_containers,
    'vzlist': get_openvz_containers,
    'virsh': get_virsh_containers,
}


def make_container_data(data):
    blank_container = {
        'environment': [],
        'names': [],
        'ips': [],
    }

    blank_container.update(data)
    return blank_container


class Containers(Plugin):
    spec = ('container', {
        'runtime': six.text_type,
        'running': bool,
        'pid': int,
        'command': six.text_type,
        'image': six.text_type,
        'id': six.text_type,
        'environment': [six.text_type],
        'names': [six.text_type],
        'ips': [six.text_type],
    })

    @staticmethod
    def prepare(settings):
        commands = COMMAND_TO_FUNC.keys()

        if not any(
            find_executable(command)
            for command in commands
        ):
            raise OSError('No container commands found: {0}'.format(commands))

    @staticmethod
    def get_state(settings):
        containers = {}

        for command, func in six.iteritems(COMMAND_TO_FUNC):
            if find_executable(command):
                containers.update(func())

        return dict(
            (key, make_container_data(data))
            for key, data in six.iteritems(containers)
        )

    @staticmethod
    def get_action_for_change(change):
        if change.type != 'updated':
            return

        if 'running' in change.data:
            was_running, _ = change.data['running']

            if was_running:
                return 'stopped'

            return 'started'

        if 'pid' in change.data:
            return 'restarted'
