from distutils.spawn import find_executable

from canaryd.packages import six

from canaryd.plugin import Plugin

from .containers_util import get_docker_containers, get_lxc_containers


class Containers(Plugin):
    spec = ('container', {
        'running': bool,
        'pid': int,
        'command': six.text_type,
        'environment': [six.text_type],
        'image': six.text_type,
        'names': [six.text_type],
        'runtime': six.text_type,
    })

    @staticmethod
    def prepare(settings):
        pass

    def get_state(self, settings):
        containers = {}

        if find_executable('docker'):
            containers.update(get_docker_containers())

        if find_executable('lxc'):
            containers.update(get_lxc_containers())

        return containers
