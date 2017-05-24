from __future__ import division

from collections import defaultdict, deque
from itertools import islice
from subprocess import CalledProcessError
from time import sleep, time

from canaryd.packages import six

from canaryd.log import logger  # noqa
from canaryd.plugin import Plugin

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
        'value': int,
        'max': int,

        # Rolling percentage averages
        '1_min_percentage': float,
        '5_min_percentage': float,
        '15_min_percentage': float,
    })

    # Disable update diff-ing - meaning generate_events always sees the full
    # state (the full state is always sent to the server). This is needed because
    # we need to check for both critical and warning, which might have different
    # average timescales - so we always need value and 1/5/15 min averages.
    diff_updates = False

    collect_interval = None

    def setup_history(self):
        # Number of items needed if one per collect interval to total 15 mins
        intervals = int(round((15 * 60) / self.collect_interval))
        logger.info('Setup interval history with {0} slots'.format(intervals))

        self.history = defaultdict(lambda: deque((), intervals))

    def prepare(self, settings):
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
            '1_min_percentage': max(60 / self.collect_interval, 1),
            '5_min_percentage': max((5 * 60) / self.collect_interval, 1),
            '15_min_percentage': max((15 * 60) / self.collect_interval, 1),
        }

        data = {}

        for key, history in six.iteritems(self.history):
            if not history:
                continue

            data[key] = history[0]

            for interval_key, interval_length in six.iteritems(intervals):
                if len(history) >= interval_length:
                    data[key][interval_key] = round(sum(
                        item['percentage']
                        for item in list(islice(history, int(interval_length)))
                    ) / interval_length, 2)

        return data

    @staticmethod
    def event_message(type_, key, data_changes):
        if type_ not in ('added', 'deleted'):
            return

        if 'type' not in data_changes:
            return

        type_name, new_type_name = data_changes['type']

        if type_ == 'added':
            type_name = new_type_name

        return '{0} {1}: {2}'.format(type_name.title(), type_, key)

    @staticmethod
    def generate_events(type_, key, data_changes, settings):
        settings_key = key

        # Swap is treated like memory (>X% warning/critical)
        if key == 'swap':
            settings_key = 'memory'

        # IO wait is *not* currently supported
        elif key == 'iowait':
            return

        elif key not in ('cpu', 'memory'):
            settings_key = 'disk'

        def make_event(type_, limit, time, changes):
            message_key = key

            if settings_key == 'cpu':
                message_key = 'CPU'

            elif settings_key != 'disk':
                message_key = message_key.title()

            message = '{0} is over {1}%'.format(message_key, limit)

            if time > 0:
                if time == 60:
                    time = '1 minute'

                elif time == 300:
                    time = '5 minutes'

                elif time == 900:
                    time = '15 minutes'

                message = '{0} has been over {1}% for {2}'.format(
                    message_key, limit, time,
                )

            if limit is None:
                message = '{0} is back to normal'.format(message_key)

            return type_, message, changes

        # If the item has been removed, resolve any lefover issues and exit
        if type_ == 'deleted':
            yield make_event('resolved', None, None, None)
            return

        time_setting_to_key = {
            0: 'percentage',
            60: '1_min_percentage',
            300: '5_min_percentage',
            900: '15_min_percentage',
        }

        # Status of over-limit values (is_warning, was_warning)
        resolved_changes = {}
        wanted_data_keys = set()

        for type_ in ('critical', 'warning'):
            enabled = getattr(
                settings,
                '{0}_{1}'.format(settings_key, type_),
            )

            if not enabled:
                continue

            limit = getattr(
                settings,
                # Eg cpu_warning_limit
                '{0}_{1}_limit'.format(settings_key, type_),
            )

            time = getattr(
                settings,
                '{0}_{1}_time_s'.format(settings_key, type_),
            )

            if time in time_setting_to_key:
                data_key = time_setting_to_key[time]
                wanted_data_keys.add(data_key)

                if data_key in data_changes:
                    old_value, value = data_changes[data_key]

                    if value > limit:
                        yield make_event(type_, limit, time, {
                            data_key: data_changes[data_key],
                        })
                        # This works because critical is run before warning
                        return

                    resolved_changes[data_key] = data_changes[data_key]

        if all(k in resolved_changes for k in wanted_data_keys):
            yield make_event('resolved', None, None, resolved_changes)
