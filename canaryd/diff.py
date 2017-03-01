from canaryd.packages import six


class Change(object):
    def __init__(self, plugin, type_, key, data=None):
        self.plugin = plugin
        self.type = type_
        self.key = key

        self.data = data

    def serialise(self):
        data = None

        if self.type == 'updated':
            data = self.plugin.serialise_update(self.data)

        elif self.type == 'added':
            data = self.plugin.serialise_item(self.data)

        return self.type, self.key, data


def make_diffs(plugin, changes):
    return [
        Change(plugin, *change)
        for change in changes
    ]


def get_state_diff(plugin, plugin_state, previous_plugin_state):
    '''
    Diffs two state dicts and returns a list of changes.

    Changes:
        All come as a tuple of ``(type, key, data, message=None)``.
    '''

    changes = []

    # Look through the previous state to find any items that have been removed
    for key, state in six.iteritems(previous_plugin_state):
        if key not in plugin_state:
            changes.append(Change(plugin, 'deleted', key))

    # Loop the new state
    for key, item in six.iteritems(plugin_state):
        previous_item = previous_plugin_state.get(key)

        # Add anything that doesn't exist
        if not previous_item:
            changes.append(Change(plugin, 'added', key, item))
            continue

        # Plugins customise diff
        if plugin.is_change(key, previous_item, item) is False:
            continue

        # Create the diff, which is a key -> (old, new) values
        state_diff = dict(
            (k, (previous_item.get(k), v))
            for k, v in six.iteritems(item)
            if v != previous_item.get(k)
        )

        if state_diff:
            changes.append(Change(plugin, 'updated', key, state_diff))

    return changes
