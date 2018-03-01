from __future__ import division

from collections import defaultdict, deque
from itertools import islice
from time import sleep, time

from canaryd.packages import six

from canaryd.log import logger  # noqa
from canaryd.plugin import Plugin
from canaryd.subprocess import CalledProcessError

from .monitor_util import get_cpu_stats, get_disk_stats, get_memory_stats


def sleep_until_interval(start, interval):
    time_taken = time() - start

    if time_taken < interval:
        sleep(interval - time_taken)


class Monitor(Plugin):
    '''
    This plugin monitors the servers basics (CPU/memory/disk/etc) and provides
    warning/critical alerts as configured on ``app.servicecanary.com``.

    Tracks:

    + CPU/IO wait usage %
    + Memory/swap usage %
    + Per disk usage %

    The actual tracking happens in a separate thread.
    '''

    spec = ('key', {
        'type': six.text_type,

        # The value, max and the % used
        'percentage': float,

        # New (>=0.3) replacements for above
        'current_value': (int, 'long'),
        'current_max': (int, 'long'),

        # Rolling time max/mins
        '1_min_max_percentage': float,
        '1_min_min_percentage': float,
        '5_min_max_percentage': float,
        '5_min_min_percentage': float,
        '15_min_max_percentage': float,
        '15_min_min_percentage': float,

        # Rolling percentage averages
        '1_min_percentage': float,
        '5_min_percentage': float,
        '15_min_percentage': float,

        # Legacy support (<0.3)
        'value': int,
        'max': int,
    })

    # Disable update diff-ing - meaning generate_events always sees the full
    # state (the full state is always sent to the server). This is needed because
    # we need to check for both critical and warning, which might have different
    # average timescales - so we always need value and 1/5/15 min averages.
    diff_updates = False

    # Don't generate events from state updates (see generate_issues_from_key_change below)
    generate_update_events = False

    # Don't log warnings when keys are missing (eg 15_min_percentage)
    warn_for_missing_keys = False

    collect_interval = None

    def setup_history(self):
        # Number of items needed if one per collect interval to total 15 mins
        intervals = int(round((15 * 60) / self.collect_interval))
        logger.info('Setup interval history with {0} slots'.format(intervals))

        self.history = defaultdict(lambda: deque((), intervals))

    def prepare(self, settings):
        if self.collect_interval != settings.collect_interval_s:
            self.collect_interval = settings.collect_interval_s
            self.setup_history()

    def get_stats(self):
        seen_keys = set()

        for type_, collector in (
            ('cpu', get_cpu_stats),
            ('memory', get_memory_stats),
            ('disk', get_disk_stats),
        ):
            try:
                stats = collector()

            except (CalledProcessError, OSError) as e:
                logger.warning('Error collecting {0} stats: {1}'.format(type_, e))
                continue

            # Push all the stats -> history
            for key, data in six.iteritems(stats):
                data['type'] = type_
                data['percentage'] = round(data['percentage'], 2)
                self.history[key].appendleft(data)
                seen_keys.add(key)

        # Remove anything not found in the latest stats
        history_keys = set(six.iterkeys(self.history))
        for key_to_remove in history_keys - seen_keys:
            self.history.pop(key_to_remove)

    def get_state(self, settings):
        # If the collect interval has changed, reset history otherwise we'll
        # generate bad averages.
        if self.collect_interval != settings.collect_interval_s:
            self.collect_interval = settings.collect_interval_s
            self.setup_history()

        # Get all the latest stats
        self.get_stats()

        intervals = {
            '1_min': max(60 / self.collect_interval, 1),
            '5_min': max((5 * 60) / self.collect_interval, 1),
            '15_min': max((15 * 60) / self.collect_interval, 1),
        }

        data = {}

        for key, history in six.iteritems(self.history):
            if not history:
                continue

            data[key] = history[0]

            for interval_key, interval_length in six.iteritems(intervals):
                if len(history) < interval_length:
                    continue

                items = [
                    item['percentage']
                    for item in islice(history, int(interval_length))
                ]

                percentage_key = '{0}_percentage'.format(interval_key)
                data[key][percentage_key] = round(sum(items) / interval_length, 2)

                min_key = '{0}_min_percentage'.format(interval_key)
                data[key][min_key] = min(items)

                max_key = '{0}_max_percentage'.format(interval_key)
                data[key][max_key] = max(items)

        return data

    @staticmethod
    def generate_issues_from_key_change(change, settings):
        key = change.key
        event_type = change.type
        data_changes = change.data

        settings_key = key

        # Swap is treated like memory (>X% warning/critical)
        if key == 'swap':
            settings_key = 'memory'

        # Anything not cpu/memory/iowait is assumed a disk
        elif key not in ('cpu', 'memory', 'iowait'):
            settings_key = 'disk'

        def make_event(alert_type, type_, limit, time, changes):
            message_key = key

            if settings_key == 'cpu':
                message_key = 'CPU'

            elif settings_key != 'disk':
                message_key = message_key.title()

            # Time=0, instant alert
            message = '{0} is over {1}%'.format(message_key, limit)

            time_to_text = {
                60: '1 minute',
                300: '5 minutes',
                900: '15 minutes',
            }

            if time > 0:
                time_text = time_to_text[time]

                if type_ == 'always':
                    message = '{0} over {1}% for {2}'.format(
                        message_key, limit, time_text,
                    )

                elif type_ == 'once':
                    message = '{0} over {1}% in the last {2}'.format(
                        message_key, limit, time_text,
                    )

                else:
                    message = '{0} average over {1}% for {2}'.format(
                        message_key, limit, time_text,
                    )

            if limit is None:
                message = '{0} is back to normal'.format(message_key)

            return alert_type, message, changes

        # If the item has been removed, resolve any lefover issues and exit
        if event_type == 'deleted':
            yield make_event('resolved', None, None, None, None)
            return

        time_setting_to_key = {
            0: 'percentage',
            60: '1_min',
            300: '5_min',
            900: '15_min',
        }

        # Status of over-limit values (is_warning, was_warning)
        resolved_changes = {}
        wanted_data_keys = set()

        for alert_type in ('critical', 'warning'):
            enabled = getattr(
                settings,
                '{0}_{1}'.format(settings_key, alert_type),
            )

            if not enabled:
                continue

            # The length of time to be over
            time = getattr(
                settings,
                '{0}_{1}_time_s'.format(settings_key, alert_type),
            )

            # Invalid time? Ignore it!
            if time not in time_setting_to_key:
                continue

            data_key = time_setting_to_key[time]

            # Always (default), average or once
            type_ = getattr(
                settings,
                '{0}_{1}_type'.format(settings_key, alert_type),
            )

            # If we're instant, use the latest/current percentage as-is
            if time > 0:
                type_to_key_formatter = {
                    'always': '{0}_min_percentage',
                    'once': '{0}_max_percentage',
                    'average': '{0}_percentage',
                }

                new_data_key = type_to_key_formatter[type_].format(data_key)

                # COMPAT w/<0.3 (no X_[min|max]_percentage)
                # Default to the rolling average as that's the only thing supported
                if new_data_key not in data_changes:
                    type_ = 'average'
                    data_key = '{0}_percentage'.format(data_key)
                else:
                    data_key = new_data_key

            # The limit to go over
            limit = getattr(
                settings,
                # Eg cpu_warning_limit
                '{0}_{1}_limit'.format(settings_key, alert_type),
            )

            wanted_data_keys.add(data_key)

            if data_key in data_changes:
                old_value, value = data_changes[data_key]

                if value > limit:
                    yield make_event(alert_type, type_, limit, time, {
                        data_key: data_changes[data_key],
                    })
                    # This works because critical is run before warning
                    return

                resolved_changes[data_key] = data_changes[data_key]

        if all(k in resolved_changes for k in wanted_data_keys):
            yield make_event('resolved', None, None, None, resolved_changes)
