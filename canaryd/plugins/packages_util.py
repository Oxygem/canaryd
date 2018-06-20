import re

from canaryd_packages import six

from canaryd.subprocess import get_command_output

DEB_REGEX = r'^[a-z]+\s+([a-zA-Z0-9\+\-\.]+):?[a-zA-Z0-9]*\s+([a-zA-Z0-9:~\.\-\+]+).+$'
RPM_REGEX = r'^([a-zA-Z0-9_\-\+]+)\-([0-9a-z\.\-]+)\.[a-z0-9_\.]+$'
PKG_REGEX = r'^([a-zA-Z0-9_\-\+]+)\-([0-9a-z\.]+)'


def get_parse_packages(timeout, package_type, command, regex, lower=True):
    output = get_command_output(
        command,
        timeout=timeout,
    )

    packages = {}

    for line in output.splitlines():
        matches = re.match(regex, line)

        if matches:
            # Sort out name
            name = matches.group(1)
            if lower:
                name = name.lower()

            packages.setdefault(name, set())
            packages[name].add(matches.group(2))

    return dict(
        (key, {
            'versions': list(value),
            'package_type': package_type,
        })
        for key, value in six.iteritems(packages)
    )


def get_deb_packages(timeout):
    return get_parse_packages(timeout, 'deb', 'dpkg -l', DEB_REGEX)


def get_rpm_packages(timeout):
    return get_parse_packages(timeout, 'rpm', 'rpm -qa', RPM_REGEX)


def get_pkg_packages(timeout):
    return get_parse_packages(timeout, 'pkg', 'pkg_info', PKG_REGEX)
