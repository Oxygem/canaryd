import json

from os import path, system

from canaryd.packages import click

from canaryd.log import logger
from canaryd.plugin import get_plugin_state, get_plugins, prepare_plugin
from canaryd.remote import CanaryJSONEncoder, register, signup
from canaryd.settings import CanarydSettings, get_config_file, write_settings_to_config

from .install_service import install_service


def init_command(key, auto_start=False):
    config_file = get_config_file()

    # Register if the config file cannot be found
    if not path.exists(config_file):
        did_register = register_command(key)

        if not did_register:
            raise TypeError('Failed to register')

    # Install the service
    click.echo('--> Installing canaryd service')
    start_command = install_service()

    if (
        auto_start or
        click.confirm(
            'Start canaryd service ({0})?'.format(start_command),
            default=True,
        )
    ):
        system(start_command)


def register_command(key):
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
    server_id = register(key=key)

    # Create our settings
    settings = CanarydSettings(api_key=key, server_id=server_id)

    # Write the settings to the config file
    write_settings_to_config(settings)

    click.echo('--> {0} written'.format(config_file))

    return True


def state_command(plugin_name):
    plugins = get_plugins()

    target_plugin = None

    for plugin in plugins:
        if plugin.name == plugin_name:
            target_plugin = plugin
            break

    if not target_plugin:
        raise TypeError('Invalid plugin: {0}'.format(plugin_name))

    prepare_plugin(target_plugin)

    click.echo('State for {0}:'.format(plugin_name))

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


def plugins_command():
    click.echo('--> Available plugins: {0}'.format(', '.join(
        plugin.name for plugin in get_plugins()
    )))
