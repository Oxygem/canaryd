from distutils.spawn import find_executable

from canaryd.packages import six

from canaryd.plugin import Plugin

from .packages_util import (
    get_deb_packages,
    get_pkg_packages,
    get_rpm_packages,
)

COMMAND_TO_FUNC = {
    'dpkg': get_deb_packages,
    'rpm': get_rpm_packages,
    'pkg_info': get_pkg_packages,
}


class Packages(Plugin):
    spec = ('package', {
        'versions': [six.text_type],
        'package_type': six.text_type,
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
        packages = {}

        for command, func in six.iteritems(COMMAND_TO_FUNC):
            if find_executable(command):
                packages.update(func())

        return packages
