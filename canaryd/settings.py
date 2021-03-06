import platform

from collections import defaultdict
from os import environ, geteuid, makedirs, path

from canaryd_packages import click, six
from canaryd_packages.six.moves.configparser import (
    DuplicateSectionError,
    Error as ConfigParserError,
    RawConfigParser,
)

from canaryd.exceptions import ConfigError
from canaryd.log import logger

VALID_STATUSES = ('DIFF', 'SYNC', 'ERROR', 'EVENTS')

API_BASE = environ.get(
    'API_BASE',
    'https://api.servicecanary.com',
)

API_VERSION = int(environ.get(
    'API_VERSION',
    1,
))

API_KEY = environ.get(
    'API_KEY',
    None,
)

SERVER_ID = environ.get(
    'SERVER_ID',
    None,
)


class CanarydSettings(object):
    api_base = API_BASE
    api_version = API_VERSION

    log_file = None
    # Rotate logs by this size (in bytes!) or a TimedRotatingFileHandler "when"
    log_file_rotation = None
    # Number of files to rotate
    log_file_rotation_count = 5

    # syslog facility to log to
    syslog_facility = None

    debug = False

    collect_interval_s = 30
    # Only collect slow plugin data this often
    slow_collect_interval_s = 900

    # API access key
    api_key = API_KEY

    # ID of (hopefully this) server attached to this key
    server_id = SERVER_ID

    def __init__(self, **kwargs):
        self.update(kwargs)

        self.plugin_settings = defaultdict(dict)

        # If no log file specified, we're root and /var/log exists, use that
        if (
            self.log_file is None
            and geteuid() <= 0
            and path.exists(path.join('/', 'var', 'log'))
        ):
            logger.debug('Root user, so setting log file to /var/log/canaryd.log')
            self.log_file = path.join('/', 'var', 'log', 'canaryd.log')

    def __getattr__(self, key):
        try:
            return super(CanarydSettings, self).__getattr__(key)
        except AttributeError:
            pass

    def to_dict(self):
        return dict(
            (key, value)
            for key, value in self.__dict__.items()
            if key != 'plugin_settings'
        )

    def update(self, data):
        changed_keys = []

        for key, value in six.iteritems(data):
            if key == 'plugin_settings':
                raise ValueError('Cannot update plugin_settings directly!')

            if getattr(self, key, None) != value:
                setattr(self, key, value)
                changed_keys.append(key)

        logger.debug('Settings updated: {0} <= {1}'.format(changed_keys, data))
        return changed_keys

    def update_plugin_settings(self, plugin_name, data):
        self.plugin_settings[plugin_name].update(data)
        logger.debug('Plugin settings updated: {0} <= {1}'.format(plugin_name, data))

    def get_plugin_settings(self, plugin_name):
        return self.plugin_settings.get(plugin_name, {})


def get_config_directory():
    # If we're non-root, just use the users config dir (~/.config, etc)
    if geteuid() > 0:
        config_directory = click.get_app_dir('canaryd')

        return config_directory

    # If we're root on OSX
    if platform.system() == 'Darwin':
        return path.join('/', 'Library', 'Application Support', 'canaryd')

    # Elsewhere on *nix (no Windows support _yet_)
    return path.join('/', 'etc', 'canaryd')


def get_config_file():
    return path.join(get_config_directory(), 'canaryd.conf')


def get_scripts_directory():
    return path.join(get_config_directory(), 'scripts')


def _get_settings(config_file=None):
    '''
    Load the config from the filesystem if provided, with defaults.
    '''

    config_file = config_file or get_config_file()

    settings = CanarydSettings()

    parser = RawConfigParser()

    if not path.exists(config_file):
        return settings

    try:
        parser.read(config_file)
    except ConfigParserError as e:
        logger.critical('Error in config file ({0}): {1}'.format(
            config_file, e.message,
        ))
        raise ConfigError('Config file error')

    canaryd_config_items = parser.items('canaryd')
    settings.update(dict(canaryd_config_items))

    for section in parser.sections():
        if not section.startswith('plugin:'):
            continue

        plugin_name = section[7:]
        plugin_config_items = parser.items(section)
        settings.update_plugin_settings(plugin_name, plugin_config_items)

    return settings


SETTINGS = None


def get_settings(config_file=None):
    '''
    Cached/public version of _get_settings.
    '''

    global SETTINGS

    if SETTINGS is None:
        SETTINGS = _get_settings(config_file=config_file)

    return SETTINGS


def write_settings_to_config(settings):
    '''
    Write a config file from settings.
    '''

    # Ensure the config directory exists
    ensure_config_directory()

    # Generate the config
    config = RawConfigParser()
    config_file = get_config_file()

    # Attempt to work alongside any existing config
    try:
        config.read(config_file)

    except ConfigParserError as e:
        logger.critical('Error in config file ({0}): {1}'.format(
            config_file, e.message,
        ))
        raise ConfigError('Config file error')

    try:
        config.add_section('canaryd')
    except DuplicateSectionError:
        pass

    for key, value in six.iteritems(settings.to_dict()):
        config.set('canaryd', key, value)

    with open(config_file, 'w') as f:
        config.write(f)


def ensure_config_directory():
    # Make sure the config directory exists
    config_directory = get_config_directory()

    if not path.exists(config_directory):
        logger.debug('Creating config directory: {0}'.format(config_directory))
        makedirs(config_directory)
