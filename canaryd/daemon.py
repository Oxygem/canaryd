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

        if status:
            state_diff = get_state_diff(
                plugin, data,
                previous_states.get(plugin, {}),
            )

            state_changes.append((plugin, (status, state_diff)))

            previous_states[plugin] = data
        else:
            logger.critical((
                'Unexpected exception while getting {0} state: '
                '{1}({2})'
            ).format(plugin.name, data.__class__.__name__, data))
            continue

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
