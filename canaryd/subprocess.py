import os
import shlex
import sys

from canaryd_packages import six
# Not ideal but using the vendored in (to requests) chardet package
from canaryd_packages.requests.packages import chardet

from canaryd.log import logger


if os.name == 'posix' and sys.version_info[0] < 3:
    from canaryd_packages.subprocess32 import *  # noqa: F403
else:
    from subprocess import *  # noqa: F403


def ensure_command_tuple(command):
    if not isinstance(command, (list, tuple)):
        return shlex.split(command)
    return command


def decode_output(output):
    if isinstance(output, six.binary_type):
        encoding = chardet.detect(output)['encoding']
        if encoding:
            output = output.decode(encoding)
        else:
            output = output.decode()

    return output


def get_command_output(command, *args, **kwargs):
    logger.debug('Executing command: {0}'.format(command))

    if not kwargs.get('shell', False):
        command = ensure_command_tuple(command)

    try:
        output = check_output(  # noqa: F405
            command,
            close_fds=True,
            stderr=STDOUT,  # noqa: F405
            *args, **kwargs
        )
    except CalledProcessError as e:  # noqa: F405
        e.output = decode_output(e.output)
        raise e

    output = decode_output(output)
    return output
