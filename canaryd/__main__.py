# canaryd
# File: canaryd/__main__.py
# Desc: entry point for canaryd

import logging

from time import time

from canaryd.packages import click  # noqa

from canaryd.daemon import run_daemon
from canaryd.log import logger, setup_file_logging, setup_logging
from canaryd.plugin import (
    cleanup_plugins,
    get_and_prepare_working_plugins,
    get_plugin_states,
)
from canaryd.remote import backoff, ping, sync_states
from canaryd.settings import get_settings
from canaryd.version import __version__


@click.command()
@click.option('-v', '--verbose', is_flag=True)
@click.option('--debug', is_flag=True)
def main(verbose, debug):
    '''
    Run the canaryd daemon.
    '''

    log_level = setup_logging(verbose, debug)

    logger.info('Starting canaryd v{0}'.format(__version__))
    logger.info('Log level set to: {0}'.format(
        logging.getLevelName(log_level),
    ))

    # Load the settings, using our config file if provided
    settings = get_settings()

    # Setup any log file
    if settings.log_file:
        setup_file_logging(settings.log_file)

    # Debug setting override
    # TODO: remove in favor of --debug
    if settings.debug == 'true':
        logger.setLevel(logging.DEBUG)

    if not settings.api_key or not settings.server_id:
        logger.critical('Missing api_key and/or server_id in config file')
        return

    # Initial ping for API presence
    logger.info('Ping API...')
    backoff(
        ping, settings,
        error_message='Could not ping',
    )

    # Load the plugin list
    plugins = get_and_prepare_working_plugins(settings)

    # Now we have plugins - capture any exception and cleanup before it raises
    try:
        # Get the initial state
        logger.info('Getting initial state...')
        start_time = time()
        states = get_plugin_states(plugins, settings)

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

        run_daemon(plugins, previous_states, settings, start_time=start_time)

    # This is OK! Cleanup plugins before exceptions propagate
    finally:
        cleanup_plugins(plugins)


try:
    main()

except KeyboardInterrupt:
    logger.info('Exiting canaryd...')

except Exception:
    # TODO: public Sentry logging

    raise
