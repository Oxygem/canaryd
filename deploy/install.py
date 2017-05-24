from pyinfra import host
from pyinfra.modules import files, pkg, server

SUDO = True


# OpenBSD doesn't come with Python!
if host.fact.os == 'OpenBSD':
    pkg.packages(
        {'Install Python 2.7'},
        'python-2.7.10',
    )

    files.link(
        {'Link python2.7 -> python'},
        '/usr/local/bin/python',
        target='/usr/local/bin/python2.7',
    )


server.shell(
    {'Install canaryd'},
    (
        # Clear the build directory so we don't break the path
        'rm -rf build/',
        # Install canaryd
        'python setup.py install',
    ),
    chdir='/opt/canaryd',
)
