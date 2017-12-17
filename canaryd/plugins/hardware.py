import json

from collections import deque

from canaryd.packages import six

from canaryd.plugin import Plugin

LSHW_CLASSES = ('bridge', 'processor', 'memory', 'disk', 'network')
TOP_LEVEL_DICT_KEYS = ('capabilities', 'configuration')
TOP_LEVEL_STRING_KEYS = (
    'serial', 'version', 'vendor',
    'product', 'handle', 'description',
    'serial_number',  # legacy support
)


def slugify(value):
    return value.lower().replace(' ', '_')


def get_lshw_items(children):
    items = []

    for item in children:
        if 'children' in item:
            items.extend(get_lshw_items(item.pop('children')))

        if item['class'] in LSHW_CLASSES:
            new_item = {
                'type': item.pop('class'),
            }

            for k in TOP_LEVEL_STRING_KEYS + TOP_LEVEL_DICT_KEYS:
                if k in item:
                    new_item[k] = item.pop(k)

            new_item['meta'] = item

            # Prefer logicalname over id
            key = item.pop('logicalname', item.pop('id'))

            items.append((key, new_item))

    return items


def get_hardware_spec():
    hardware_spec = {
        'type': six.text_type,
        'meta': dict,
    }

    for key in TOP_LEVEL_STRING_KEYS:
        hardware_spec[key] = six.text_type

    for key in TOP_LEVEL_DICT_KEYS:
        hardware_spec[key] = dict

    return hardware_spec


class Hardware(Plugin):
    spec = ('key', get_hardware_spec())

    command = 'lshw -json'
    current_state = None

    def __init__(self):
        self.previous_states = deque((), 2)

    def parse(self, output):
        # Parse and generate state
        lshw_data = json.loads(output)
        data = get_lshw_items(lshw_data.get('children', []))

        self.previous_states.append(dict(data))

        # First call? Just return the state
        if len(self.previous_states) == 1:
            self.current_state = self.previous_states[0]
            return self.current_state

        other_state, latest_state = self.previous_states

        for key, item in six.iteritems(latest_state):
            # New item not in previous state? OK!
            if key not in other_state:
                self.current_state[key] = item

            # Item is same as previous state? OK!
            elif key in other_state and all(
                other_state[key].get(k) == item.get(k)
                for k in TOP_LEVEL_STRING_KEYS
            ):
                self.current_state[key] = item

        # Remove any items dropped from current state in latest_state
        for key, item in six.iteritems(self.current_state):
            if key not in latest_state:
                del self.current_state[key]

        return self.current_state

    @staticmethod
    def is_change(item_key, previous_item, item):
        # If any of our top level keys (serial, vendor, product, etc) change,
        # count as a change. Anything nested (meta, capabilities, etc) is ignored.
        for key in TOP_LEVEL_STRING_KEYS:
            if previous_item.get(key) != item.get(key):
                return True

        return False
