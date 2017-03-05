from os import geteuid

from canaryd.packages import click

from canaryd.exceptions import UserCancelError
from canaryd.settings import get_config_directory


def check_root():
    # If we're root, we're all good!
    if geteuid() <= 0:
        return

    # Warn the user about the implications of running as non-root
    click.echo(click.style('''
Not root user, using config directory:
{0}
It is recommended to run canaryd as root as
plugins that require privileges (eg iptables)
will not function properly.
'''.strip().format(get_config_directory()), 'yellow'))

    # Confirm this is OK!
    if not click.confirm('Do you wish to continue?'):
        raise UserCancelError()
