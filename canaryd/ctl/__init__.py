# cansryd
# File: canaryd/canaryct/__init__.py
# Desc: canaryctl functions

from __future__ import print_function

import json

from os import path, system

from canaryd.packages import click

from canaryd.log import logger, setup_logging
from canaryd.plugin import (
    get_plugin_state,
    get_plugins,
    get_plugin_by_name,
    prepare_plugin,
)
from canaryd.remote import CanaryJSONEncoder, register_server, signup
from canaryd.settings import (
    CanarydSettings,
    get_config_file,
    write_settings_to_config,
)
from canaryd.version import __version__

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
def init(start, key):
    '''
    Create the canaryd service and start it.

    This command will attempt to register if the config file is not found.
    '''

    config_file = get_config_file()

    # Register if the config file cannot be found
    if not path.exists(config_file):
        did_register = register(key)

        if not did_register:
            raise TypeError('Failed to register')

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

    config_file = get_config_file()

    if not key:
        click.echo('--> No key provided or set for this instance')
        click.echo('--> To sign up, input your email address, or blank to skip')
        email_or_blank = raw_input('Email or blank: ')

        if '@' not in email_or_blank:
            return False

        # Signup and get the key
        key = signup(email_or_blank)
        click.echo('--> You are now signed up for servicecanary.com')
        click.echo('--> Check your email for a login link to view updates')

    # Register the server
    server_id = register_server(key=key)

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
