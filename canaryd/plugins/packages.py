from distutils.spawn import find_executable

from canaryd.packages import six

from canaryd.plugin import Plugin

from .packages_util import (
    get_deb_packages,
    get_pkg_packages,
    get_rpm_packages,
)


class Packages(Plugin):
    spec = ('package', {
        'versions': [six.text_type],
        'package_type': six.text_type,
    })

    @staticmethod
    def prepare(settings):
        pass

    @staticmethod
    def get_state(settings):
        packages = {}

        if find_executable('dpkg'):
            packages.update(get_deb_packages())

        if find_executable('rpm'):
            packages.update(get_rpm_packages())

        if find_executable('pkg_info'):
            packages.update(get_pkg_packages())

        return packages
