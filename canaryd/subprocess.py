import os
import sys


if os.name == 'posix' and sys.version_info[0] < 3:
    from canaryd.packages.subprocess32 import *  # noqa
else:
    from subprocess import *  # noqa


def get_command_output(command, *args, **kwargs):
    return check_output(  # noqa
        command,
        shell=True,
        close_fds=True,
        *args, **kwargs
    )
