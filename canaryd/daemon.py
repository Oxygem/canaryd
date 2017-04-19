# canaryd
# File: canaryd/daemon.py
# Desc: the canaryd daemon

from time import sleep, time

from canaryd.diff import get_state_diff
from canaryd.log import logger
from canaryd.plugin import get_plugin_states
from canaryd.remote import ApiError, backoff, upload_state_changes


def _sleep_until_interval(start, interval):
    time_taken = time() - start

    if time_taken < interval:
        sleep(interval - time_taken)


def _daemon_loop(plugins, previous_states, settings):
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

    try:
        settings_changes = backoff(
            upload_state_changes,
            state_changes,
            settings,
        )

        if settings_changes:
            changed_keys = settings.update(settings_changes)
            if changed_keys:
                logger.info('Remote settings update: {0}'.format(
                    ', '.join(changed_keys),
                ))

    except ApiError as e:
        e.log()


def run_daemon(plugins, previous_states, settings, start_time=None):
    if start_time:
        _sleep_until_interval(
            start_time, settings.collect_interval_s,
        )

    while True:
        start = time()

        _daemon_loop(plugins, previous_states, settings)

        _sleep_until_interval(
            start, settings.collect_interval_s,
        )
