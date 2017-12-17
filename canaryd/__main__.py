# canaryd
# File: canaryd/__main__.py
# Desc: entry point for canaryd

import logging

from time import time

from canaryd.packages import click  # noqa

from canaryd.daemon import run_daemon
from canaryd.log import logger, setup_logging, setup_logging_from_settings
from canaryd.plugin import (
    get_and_prepare_working_plugins,
    get_plugin_states,
)
from canaryd.remote import backoff, ping, sync_states
from canaryd.settings import ensure_config_directory, get_settings
from canaryd.version import __version__


@click.command(context_settings={'help_option_names': ['-h', '--help']})
@click.option('-v', '--verbose', is_flag=True)
@click.option('-d', '--debug', is_flag=True)
@click.version_option(
    version=__version__,
    prog_name='canaryd',
    message='%(prog)s: v%(version)s',
)
def main(verbose, debug):
    '''
    Run the canaryd daemon.
    '''

    log_level = setup_logging(verbose, debug)

    logger.info('Starting canaryd v{0}'.format(__version__))
    logger.info('Log level set to: {0}'.format(
        logging.getLevelName(log_level),
    ))

    # Ensure the config directory exists
    ensure_config_directory()

    # Load the settings, using our config file if provided
    settings = get_settings()

    # Setup any log file/syslog
    setup_logging_from_settings(settings)

    # Settings can set debug on if needed
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
        max_wait=settings.collect_interval_s,
    )

    # Load the plugin list
    plugins = get_and_prepare_working_plugins(settings)

    # Get the initial state
    logger.info('Getting initial state...')
    start_time = time()
    states = get_plugin_states(plugins, settings)

    # Sync this state and get settings
    logger.info('Syncing initial state...')

    remote_settings = backoff(
        sync_states, states, settings,
        error_message='Could not sync state',
        max_wait=settings.collect_interval_s,
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

    run_daemon(previous_states, settings, start_time=start_time)


try:
    main()

except Exception:
    # TODO: public Sentry logging

    raise
