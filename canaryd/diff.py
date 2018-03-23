from canaryd_packages import six

from canaryd.log import logger


class Change(object):
    def __init__(self, plugin, type_, key, data=None):
        self.plugin = plugin
        self.type = type_
        self.key = key

        # COMPAT w/canaryd < 0.2
        # Legacy support where added/deleted would either have data/None,
        # rather than data changes (where every key: (old_value, new_value)).
        if data and self.type in ('added', 'deleted') and not all(
            isinstance(item, (tuple, list)) and len(item) == 2
            for _, item in six.iteritems(data)
        ):
            if self.type == 'added':
                data = dict(
                    (key, (None, value))
                    for key, value in six.iteritems(data)
                )

            elif self.type == 'deleted':
                data = dict(
                    (key, (value, None))
                    for key, value in six.iteritems(data)
                )

            logger.info('Converted legacy data: {0}'.format(data))

        self.data = data

    def serialise(self):
        return self.type, self.key, self.data

    def __repr__(self):
        return 'Change: {0}'.format((self.plugin, self.type, self.key, self.data))


def make_diffs(plugin, changes):
    return [
        Change(plugin, *change)
        for change in changes
    ]


def get_state_diff(plugin, plugin_state, previous_plugin_state):
    '''
    Diffs two state dicts and returns a list of changes.

    Changes:
        All come as a tuple of ``(plugin, type, key, data=None)``.
    '''

    changes = []

    # Look through the previous state to find any items that have been removed
    for key, previous_item in six.iteritems(previous_plugin_state):
        if key not in plugin_state:
            state_diff = dict(
                (k, (v, None))
                for k, v in six.iteritems(previous_item)
            )

            changes.append(Change(plugin, 'deleted', key, data=state_diff))

    # Loop the new state
    for key, item in six.iteritems(plugin_state):
        previous_item = previous_plugin_state.get(key)

        # Add anything that doesn't exist
        if not previous_item:
            state_diff = dict(
                (k, (None, v))
                for k, v in six.iteritems(item)
            )
            changes.append(Change(plugin, 'added', key, data=state_diff))
            continue

        # Create the diff, which is a key -> (old, new) values
        all_keys = list(six.iterkeys(item)) + list(six.iterkeys(previous_item))
        all_keys = set(all_keys)

        state_diff = dict(
            (k, (previous_item.get(k), item.get(k)))
            for k in all_keys
            if item.get(k) != previous_item.get(k)
        )

        # If something changed - send the event!
        if state_diff:
            # If this plugin disables diffs, remake the state diff w/everything
            if not plugin.diff_updates:
                state_diff = dict(
                    (k, (previous_item.get(k), v))
                    for k, v in six.iteritems(item)
                )

            changes.append(Change(plugin, 'updated', key, data=state_diff))

    return changes
