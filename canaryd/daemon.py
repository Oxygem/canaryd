# canaryd
# File: canaryd/daemon.py
# Desc: the canaryd daemon

from time import sleep, time

from canaryd.diff import get_state_diff
from canaryd.log import logger
from canaryd.plugin import (
    get_and_prepare_working_plugins,
    get_plugin_states,
)
from canaryd.remote import backoff, upload_state_changes


def _sleep_until_interval(start, interval):
    time_taken = time() - start

    if time_taken < interval:
        sleep(interval - time_taken)


def _daemon_loop(previous_states, settings):
    logger.info('Getting plugin states...')

    # Load the plugin list
    plugins = get_and_prepare_working_plugins(settings)

    states = get_plugin_states(plugins, settings)
    state_changes = []

    for plugin, status_data in states:
        status, data = status_data

        # Plugin ran OK and we have state!
        if status:
            previous_state = previous_states.get(plugin, {})

            # If the previous state was good - ie not an Exception instance - this
            # prevents first-failing then working plugin from generating addition
            # events on first successful run.
            if isinstance(previous_state, dict):
                state_diff = get_state_diff(plugin, data, previous_state)
                state_changes.append((plugin, (status, state_diff)))

            # Because we don't know the previous working state, send the whole
            # state obj to the server to diff, like the initial sync.
            else:
                state_changes.append((plugin, ('SYNC', data)))

            # Set the previous state
            previous_states[plugin] = data

        # Plugin raised an exception, fail!
        else:
            logger.critical((
                'Unexpected exception while getting {0} state: '
                '{1}({2})'
            ).format(plugin.name, data.__class__.__name__, data))

            # Send the failed exception to the server, generating a warning
            exception_data = {
                'class': data.__class__.__name__,
                'message': '{0}'.format(data),
                'traceback': getattr(data, '_traceback'),
            }
            state_changes.append((plugin, ('ERROR', exception_data)))

    logger.info('Uploading state changes...')

    settings_changes = backoff(
        upload_state_changes,
        state_changes,
        settings,
        error_message='Could not sync state changes',
        max_wait=settings.collect_interval_s,
    )

    if settings_changes:
        changed_keys = settings.update(settings_changes)
        if changed_keys:
            logger.info('Remote settings update: {0}'.format(
                ', '.join(changed_keys),
            ))


def run_daemon(previous_states, settings, start_time=None):
    if start_time:
        _sleep_until_interval(
            start_time, settings.collect_interval_s,
        )

    while True:
        start = time()

        _daemon_loop(previous_states, settings)

        _sleep_until_interval(
            start, settings.collect_interval_s,
        )
