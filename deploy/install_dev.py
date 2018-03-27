from pyinfra import host
from pyinfra.modules import files, pkg, server

SUDO = True


# OpenBSD doesn't come with Python!
if host.name == '@vagrant/openbsd58':
    pkg.packages(
        {'Install Python 2.7'},
        'python-2.7',
    )

    files.link(
        {'Link python2.7 -> python'},
        '/usr/local/bin/python',
        target='/usr/local/bin/python2.7',
    )


server.shell(
    {'Install pip'},
    (
        'wget https://bootstrap.pypa.io/get-pip.py',
        'python get-pip.py',
    ),
)


server.shell(
    {'Install canaryd'},
    (
        # Install canaryd
        'python setup.py develop',
    ),
    chdir='/opt/canaryd',
    serial=True,
)
