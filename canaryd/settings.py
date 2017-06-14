# canaryd
# File: canaryd/settings.py
# Desc: settings for canaryd/canaryctl

import platform

from os import environ, geteuid, listdir, makedirs, path
from shutil import copy

from canaryd.packages import click, six  # noqa
from canaryd.packages.six.moves.configparser import (  # noqa
    DuplicateSectionError,
    Error as ConfigParserError,
    RawConfigParser,
)

from canaryd.exceptions import ConfigError
from canaryd.log import logger

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
    debug = False

    collect_interval_s = 30

    # API access key
    api_key = API_KEY

    # ID of (hopefully this) server attached to this key
    server_id = SERVER_ID

    def __init__(self, **kwargs):
        self.update(kwargs)

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

    def update(self, data):
        changed_keys = []

        for key, value in six.iteritems(data):
            if getattr(self, key, None) != value:
                setattr(self, key, value)
                changed_keys.append(key)

        logger.debug('Settings updated: {0} <= {1}'.format(changed_keys, data))
        return changed_keys


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


def get_settings(config_file=None):
    '''
    Load the config from the filesystem if provided, with defaults.
    '''

    config_file = config_file or get_config_file()

    settings = CanarydSettings(config_file=config_file)

    parser = RawConfigParser()

    if path.exists(config_file):
        try:
            parser.read(config_file)
            canaryd_config_items = parser.items('canaryd')

            settings.update(dict(canaryd_config_items))
            settings.update(dict(canaryd_config_items))

        except ConfigParserError as e:
            logger.critical('Error in config file ({0}): {1}'.format(
                config_file, e.message,
            ))
            raise ConfigError('Config file error')

    return settings


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

    for key, value in six.iteritems(settings.__dict__):
        config.set('canaryd', key, value)

    with open(config_file, 'wb') as f:
        config.write(f)


def copy_builtin_scripts():
    # Copy built in scripts to the scripts/available directory
    available_scripts_directory = path.join(get_scripts_directory(), 'available')

    logger.debug(
        'Copying default scripts to: {0}'.format(available_scripts_directory),
    )

    builtin_scripts_directory = path.join(path.dirname(__file__), 'scripts')

    for file in listdir(builtin_scripts_directory):
        copy(
            path.join(builtin_scripts_directory, file),
            path.join(available_scripts_directory, file),
        )


def ensure_config_directory():
    # Make sure the config directory exists
    config_directory = get_config_directory()

    if not path.exists(config_directory):
        logger.debug('Creating config directory: {0}'.format(config_directory))
        makedirs(config_directory)

    # Make sure the scripts directory exists
    scripts_directory = get_scripts_directory()

    if not path.exists(scripts_directory):
        logger.debug('Creating scripts directory: {0}'.format(scripts_directory))

        # Make the scripts, scripts/enabled & scripts/available directories
        makedirs(path.join(scripts_directory, 'enabled'))
        makedirs(path.join(scripts_directory, 'available'))

        copy_builtin_scripts()
