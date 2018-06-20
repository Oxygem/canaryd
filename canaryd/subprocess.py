import os
import shlex
import sys

from canaryd_packages import six
# Not ideal but using the vendored in (to requests) chardet package
from canaryd_packages.requests.packages import chardet

from canaryd.log import logger


if os.name == 'posix' and sys.version_info[0] < 3:
    from canaryd_packages.subprocess32 import *  # noqa
else:
    from subprocess import *  # noqa


def get_command_output(command, *args, **kwargs):
    logger.debug('Executing command: {0}'.format(command))

    if (
        not kwargs.get('shell', False)
        and not isinstance(command, (list, tuple))
    ):
        command = shlex.split(command)

    output = check_output(  # noqa
        command,
        close_fds=True,
        stderr=STDOUT,  # noqa
        *args, **kwargs
    )

    if isinstance(output, six.binary_type):
        encoding = chardet.detect(output)['encoding']
        output = output.decode(encoding)

    return output
