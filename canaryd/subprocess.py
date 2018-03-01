import os
import shlex
import sys

from canaryd.packages import six  # noqa

from canaryd.log import logger


if os.name == 'posix' and sys.version_info[0] < 3:
    from canaryd.packages.subprocess32 import *  # noqa
else:
    from subprocess import *  # noqa


def get_command_output(command, *args, **kwargs):
    logger.debug('Executing command: {0}'.format(command))

    if not kwargs.get('shell', False):
        if isinstance(command, six.text_type):
            command = command.encode()

        if not isinstance(command, (list, tuple)):
            command = shlex.split(command)

    return check_output(  # noqa
        command,
        close_fds=True,
        stderr=STDOUT,  # noqa
        *args, **kwargs
    )
