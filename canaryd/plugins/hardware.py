from canaryd.packages import six
from canaryd.packages.dmidecode import parse_dmi

from canaryd.plugin import Plugin


def slugify(value):
    return value.lower().replace(' ', '_')


class Hardware(Plugin):
    spec = ('key', {
        'type': six.text_type,
        'serial_number': six.text_type,
        'version': six.text_type,
        'meta': dict,
    })

    command = 'dmidecode'

    @staticmethod
    def parse(output):
        dmi_data = parse_dmi(output)

        data = []

        for key, meta in dmi_data:
            # Make _title -> title
            meta['title'] = meta.pop('_title')

            meta = dict(
                (slugify(k), value)
                for k, value in six.iteritems(meta)
            )

            item = {}
            for k in ('type', 'serial_number', 'version'):
                if k in meta:
                    item[k] = meta.pop(k)

            item['meta'] = meta

            data.append((slugify(key), item))

        return dict(data)
