from glob import glob
from hashlib import sha1
from os import path

from canaryd_packages import six

from canaryd.plugin import Plugin

BUFFER_SIZE = 65536
PATHS_TO_TRACK = (
    '/etc/*',
    '/boot/*',
    '/dev/*',
    '/bin/*',
    '/sbin/*',
    '/usr/bin/*',
    '/usr/sbin/*',
)


def get_file_hash(filename):
    sha = sha1()

    with open(filename, 'rb') as f:
        while True:
            data = f.read(BUFFER_SIZE)
            if not data:
                break

            sha.update(data)
    return sha.hexdigest()


class Integrity(Plugin):
    '''
    Tracks the integrity of system files by checking their owner, permissions
    and checksum hashes.
    '''

    spec = ('filename', {
        'sha1_hash': six.text_type,
    })

    is_slow = True

    def prepare(self, settings):
        return True

    def get_state(self, settings):
        file_hashes = {}

        for path_to_track in PATHS_TO_TRACK:
            for filename in glob(path_to_track):
                if not path.isfile(filename):
                    continue

                try:
                    file_hash = get_file_hash(filename)
                except (OSError, IOError):
                    pass
                else:
                    file_hashes[filename] = {
                        'sha1_hash': file_hash,
                    }

        return file_hashes
