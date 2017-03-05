from os import geteuid

from canaryd.packages import click

from canaryd.exceptions import CanarydError, UserCancelError


def check_root(message, exit=False):
    # If we're root, we're all good!
    if geteuid() <= 0:
        return

    message = click.style(message, 'yellow')

    # If exit, just fail
    if exit:
        raise CanarydError(message)

    # Warn the user about the implications of running as non-root
    click.echo(message)

    # Confirm this is OK!
    if not click.confirm('Do you wish to continue?'):
        raise UserCancelError()
