# canaryd
# File: canaryd/__main__.py
# Desc: entry point for canaryd

import logging

from time import time

from canaryd.packages import click  # noqa

from canaryd.daemon import run_daemon
from canaryd.log import logger, setup_logging, setup_file_logging
from canaryd.plugin import get_and_prepare_working_plugins, get_plugin_states
from canaryd.remote import backoff, ping, sync_states
from canaryd.settings import get_config_file, get_settings
from canaryd.version import __version__


@click.command()
@click.option('-v', '--verbose', count=True)
def main(verbose=0):
    '''
    Run the canaryd daemon.
    '''

    setup_logging(verbose)
    logger.info('Starting canaryd v{0}'.format(__version__))

    config_file = get_config_file()

    # Load the settings, using our config file if provided
    settings = get_settings(config_file)

    # Setup any log file
    if settings.log_file:
        setup_file_logging(settings.log_file)

    # Debug setting override
    if settings.debug == 'true':
        logger.setLevel(logging.DEBUG)

    if not settings.api_key or not settings.server_id:
        logger.critical('Missing api_key and/or server_id in config file')
        return

    # Initial ping for API presence
    backoff(
        ping, settings,
        error_message='Could not ping',
    )

    # Load the plugin list
    plugins = get_and_prepare_working_plugins()

    # Get the initial state
    logger.info('Getting initial state...')
    start_time = time()
    states = get_plugin_states(plugins)

    # Sync this state and get settings
    logger.info('Syncing initial state...')

    remote_settings = backoff(
        sync_states, states, settings,
        error_message='Could not sync state',
    )

    # Update settings w/remote ones
    settings.update(remote_settings)

    # Run the loop
    logger.info('Starting daemon loop...')

    # Make previous states dict
    previous_states = dict(
        (plugin, status_data[1])
        for plugin, status_data in states
        if status_data[0]
    )

    try:
        run_daemon(plugins, previous_states, settings, start_time=start_time)

    # This is OK!
    except KeyboardInterrupt:
        logger.info('Exiting canaryd...')


main()
