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

    '/lib/*',
    '/usr/lib/*',
    '/usr/local/lib/*',
    '/lib64/*',
    '/usr/lib64/*',

    '/bin/*',
    '/sbin/*',
    '/usr/bin/*',
    '/usr/sbin/*',
    '/usr/local/bin/*',
    '/usr/local/sbin/*',
    '/opt/bin/*',
    '/opt/sbin/*',
)
PATHS_TO_IGNORE = (
    '/etc/adjtime',
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

    def get_files_to_check(self, settings):
        plugin_settings = settings.get_plugin_settings('integrity')

        paths_to_check = set(PATHS_TO_TRACK)
        user_paths_to_check = plugin_settings.get('check_paths')
        if user_paths_to_check:
            paths_to_check.update(user_paths_to_check.split())

        checked_files = set()

        for path_to_track in paths_to_check:
            for filename in glob(path_to_track):
                if (
                    filename in PATHS_TO_IGNORE
                    or not path.isfile(filename)
                ):
                    continue

                if filename not in checked_files:
                    checked_files.add(filename)
                    yield filename

    def get_state(self, settings):
        file_hashes = {}
        for filename in self.get_files_to_check(settings):
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
