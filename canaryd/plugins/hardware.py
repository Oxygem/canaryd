import json

from canaryd.packages import six

from canaryd.plugin import Plugin

LSHW_CLASSES = ('bridge', 'processor', 'memory', 'disk', 'network')
TOP_LEVEL_DICT_KEYS = ('capabilities', 'configuration')
TOP_LEVEL_STRING_KEYS = (
    'serial', 'version', 'vendor',
    'product', 'description', 'handle',
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

    @staticmethod
    def parse(output):
        lshw_data = json.loads(output)
        data = get_lshw_items(lshw_data.get('children', []))

        return dict(data)

    @staticmethod
    def is_change(key, previous_item, item):
        # If any of our top level keys (serial, vendor, product, etc) change,
        # count as a change. Anything nested (meta, capabilities, etc) is ignored.
        for key in TOP_LEVEL_STRING_KEYS:
            if previous_item.get(key) != item.get(key):
                return True

        return False
