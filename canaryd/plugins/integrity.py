from glob import glob
from hashlib import sha1
from os import path, stat

from canaryd_packages import six

from canaryd.plugin import Plugin

# Attempt to import pwd/grp - only supported on *nix
try:
    import pwd
    import grp
except ImportError:
    pwd = None
    grp = None


BUFFER_SIZE = 65536
MAX_SIZE = 1024 ** 3  # 1GB
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

    spec = ('file', {
        'sha1_hash': six.text_type,
        'size': int,
        'user': six.text_type,
        'group': six.text_type,
        'permissions': six.text_type,
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

                stat_data = stat(filename)

                if stat_data.st_size > MAX_SIZE:
                    continue

                file_data = {
                    'size': stat_data.st_size,
                    'permissions': format(stat_data.st_mode, 'o'),
                }

                if pwd:
                    file_data['user'] = pwd.getpwuid(stat_data.st_uid).pw_name

                if grp:
                    file_data['group'] = grp.getgrgid(stat_data.st_gid).gr_name

                try:
                    file_data['sha1_hash'] = get_file_hash(filename)
                except (OSError, IOError):
                    pass

                file_hashes[filename] = file_data

        return file_hashes
