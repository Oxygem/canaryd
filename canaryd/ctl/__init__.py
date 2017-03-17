# cansryd
# File: canaryd/canaryct/__init__.py
# Desc: canaryctl functions

from __future__ import print_function

import json

from os import path, system

from canaryd.packages import click

from canaryd import remote

from canaryd.exceptions import CanarydError
from canaryd.log import logger, setup_logging
from canaryd.plugin import (
    get_plugin_state,
    get_plugins,
    get_plugin_by_name,
    prepare_plugin,
)
from canaryd.remote import CanaryJSONEncoder
from canaryd.settings import (
    CanarydSettings,
    get_config_directory,
    get_config_file,
    get_settings,
    write_settings_to_config,
)
from canaryd.version import __version__

from .check_root import check_root
from .install_service import install_service


# Parse arguments
@click.group()
@click.option('-v', '--verbose', count=True)
def main(verbose=0):
    '''
    canaryd control.
    '''

    # For canaryctl we want warnings to show, so always bump verbosity
    verbose += 1
    setup_logging(verbose)


@main.command()
@click.option('--start', is_flag=True, default=False)
@click.argument('key', required=False)
@click.pass_context
def init(ctx, start, key):
    '''
    Create the canaryd service and start it.

    This command will attempt to register if the config file is not found.
    '''

    check_root('Not root user, cannot create services.', exit=True)

    config_file = get_config_file()

    # Register if the config file cannot be found
    if not path.exists(config_file):
        did_register = ctx.invoke(register, key=key)

        if not did_register:
            raise CanarydError('Failed to register')

    # Install the service
    click.echo('--> Installing canaryd service')
    start_command = install_service()

    if (
        start or
        click.confirm(
            'Start canaryd service ({0})?'.format(start_command),
            default=True,
        )
    ):
        system(start_command)


@main.command()
@click.argument('key', required=False)
def register(key):
    '''
    Register this server on Service Canary.

    If no api key is provided, you can sign up instantly.
    '''

    check_root('''
Not root user, using config directory:
{0}
It is recommended to run canaryd as root as
plugins that require privileges (eg iptables)
will not function properly.
'''.strip().format(get_config_directory()))

    config_file = get_config_file()

    if not key:
        click.echo('--> No key provided or set for this instance')
        click.echo('--> To sign up, input your email address, or blank to skip')
        email_or_blank = raw_input('Email or blank: ')

        if '@' not in email_or_blank:
            return False

        # Signup and get the key
        did_signup, key_or_message = remote.signup(email_or_blank)

        if did_signup:
            key = key_or_message
            click.echo('--> You are now signed up for servicecanary.com.')
            click.echo('--> Check your email for a login link to view updates.')

        else:
            click.echo(click.style(key_or_message, 'blue'))
            return False

    # Register the server
    server_id = remote.register(key=key)

    # Create our settings
    settings = CanarydSettings(api_key=key, server_id=server_id)

    # Write the settings to the config file
    write_settings_to_config(settings)

    click.echo('--> {0} written'.format(config_file))

    return True


@main.command()
@click.argument('plugin')
def state(plugin):
    '''
    Get state for a single plugin.
    '''

    # Trigger load of all plugins first
    get_plugins()

    target_plugin = get_plugin_by_name(plugin)

    if not target_plugin:
        raise TypeError('Invalid plugin: {0}'.format(plugin))

    prepare_plugin(target_plugin)

    click.echo('State for {0}:'.format(plugin))

    status, data = get_plugin_state(target_plugin)

    if status:
        print(json.dumps(
            target_plugin.serialise_state(data),
            cls=CanaryJSONEncoder,
            indent=4,
        ))
    else:
        logger.critical((
            'Unexpected exception while getting {0} state: '
            '{1}({2})'
        ).format(plugin.name, data.__class__.__name__, data))


@main.command()
def plugins():
    '''
    List all plugins.
    '''

    click.echo('--> Available plugins: {0}'.format(', '.join(
        plugin.name for plugin in get_plugins()
    )))


@main.command()
def version():
    '''
    Print the canaryd version and config location.
    '''

    click.echo('canaryd: v{0}'.format(__version__))
    click.echo('config: {0}'.format(get_config_file()))


@main.command()
def ping():
    '''
    Ping servicecanary.com.
    '''

    config_file = get_config_file()

    if not path.exists(config_file):
        click.echo((
            'No config file ({0}) exists, '
            'please run `canaryctl init`'
        ).format(config_file))
        return

    settings = get_settings(config_file)

    # Ping the API
    remote.ping(settings)

    click.echo('OK!')
