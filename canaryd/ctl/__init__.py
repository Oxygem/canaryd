# canaryd
# File: canaryd/canaryctl/__init__.py
# Desc: canaryctl functions

from __future__ import print_function

import json
import logging

from os import path, system

from canaryd.packages import click  # noqa

from canaryd import remote

from canaryd.exceptions import CanarydError
from canaryd.log import logger, setup_logging
from canaryd.plugin import (
    get_and_prepare_working_plugins,
    get_plugin_by_name,
    get_plugin_state,
    get_plugins,
    prepare_plugin,
)
from canaryd.remote import ApiError, CanaryJSONEncoder, create_event

from canaryd.settings import (
    ensure_config_directory,
    get_config_directory,
    get_config_file,
    get_settings,
    write_settings_to_config,
)
from canaryd.version import __version__

from .check_root import check_root
from .install_service import install_service


# Parse arguments
@click.group(context_settings={'help_option_names': ['-h', '--help']})
@click.option('-v', '--verbose', is_flag=True)
@click.option('-d', '--debug', is_flag=True)
@click.version_option(
    version=__version__,
    prog_name='canaryctl',
    message='%(prog)s: v%(version)s',
)
def main(verbose, debug):
    '''
    canaryd control.
    '''

    log_level = setup_logging(verbose, debug)

    logger.info('Starting canaryctl v{0}'.format(__version__))
    logger.info('Log level set to: {0}'.format(
        logging.getLevelName(log_level),
    ))

    # Ensure the scripts directory (in config) exists
    ensure_config_directory()


@main.command()
@click.option('--start', is_flag=True, default=False)
@click.option('--enable', is_flag=True, default=False)
@click.argument('key', required=False)
@click.pass_context
def init(ctx, start, enable, key):
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
            raise CanarydError(click.style('Failed to register', 'red'))

    # Install the service
    click.echo('--> Installing canaryd service')
    start_command, enable_command = install_service()

    if (
        start or
        click.confirm(
            'Start canaryd service ({0})?'.format(start_command),
            default=True,
        )
    ):
        system(start_command)

    if enable_command and (
        enable or
        click.confirm(
            'Enable canaryd service ({0})?'.format(enable_command),
            default=True,
        )
    ):
        system(enable_command)


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
    settings = get_settings()
    settings.api_key = key
    settings.server_id = server_id

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

    settings = get_settings()
    target_plugin = get_plugin_by_name(plugin)

    if not target_plugin:
        raise CanarydError(click.style(
            'Invalid plugin: {0}'.format(plugin),
            'red',
        ))

    prepare_status = prepare_plugin(target_plugin, settings)

    if prepare_status is not True:
        _, e = prepare_status
        raise CanarydError(click.style(
            'Plugin unavailable: {0} ({1})'.format(target_plugin.name, e),
            'yellow',
        ))

    click.echo('State for {0}:'.format(plugin))

    status, data = get_plugin_state(target_plugin, settings)

    if status:
        print(json.dumps(
            data,
            cls=CanaryJSONEncoder,
            indent=4,
        ))
    else:
        raise CanarydError(click.style(
            'Unexpected exception while getting {0} state: {1}({2})'.format(
                target_plugin.name,
                data.__class__.__name__,
                data,
            ),
            'red',
            bold=True,
        ))


@main.command()
def plugins():
    '''
    List available and enabled plugins.
    '''

    click.echo('--> Available plugins: {0}'.format(', '.join(
        plugin.name for plugin in get_plugins()
    )))

    working_plugins = get_and_prepare_working_plugins(get_settings())

    click.echo('--> Enabled plugins:')
    for plugin in working_plugins:
        click.echo(click.style('    {0}'.format(plugin.name), bold=True))


@main.command()
def status():
    '''
    Print the current status of canaryd.
    '''

    config_file = get_config_file()

    click.echo('config file: {0}'.format(config_file))

    if not path.exists(config_file):
        click.echo((
            'No config file ({0}) exists, '
            'please run `canaryctl init`'
        ).format(config_file))
        return

    settings = get_settings()

    try:
        remote.ping(settings)
        status = click.style('online', 'green')

    except ApiError as e:
        e.log()
        status = click.style('offline', 'red')

    click.echo('connection: {0}'.format(status))


@main.command()
@click.argument('plugin')
@click.argument('type')
@click.argument('description')
@click.argument('data', required=False)
def event(plugin, type, description, data=None):
    '''
    Push a custom event to Service Canary.
    '''

    settings = get_settings()

    if data:
        data = json.loads(data)

    response_data = create_event(settings, plugin, type, description, data)

    if response_data['created']:
        click.echo('Event created: {0}'.format(
            click.style(response_data['event_id'], bold=True),
        ))
    else:
        click.echo(click.style('Event not created', 'red'))
