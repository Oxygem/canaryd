# canaryd
# File: canaryd/settings.py
# Desc: settings for canaryd/canaryctl

import platform

from ConfigParser import (
    DuplicateSectionError,
    Error as ConfigParserError,
    RawConfigParser,
)
from os import environ, geteuid, makedirs, path

from canaryd.packages import click, six

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

    collect_interval_s = 60

    # API access key
    api_key = API_KEY

    # ID of (hopefully this) server attached to this key
    server_id = SERVER_ID

    def __init__(self, **kwargs):
        self.update(kwargs)

    def update(self, data):
        for key, value in six.iteritems(data):
            setattr(self, key, value)

        logger.debug('Settings updated: {0}'.format(data))


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


def get_settings(config_file):
    '''
    Load the config from the filesystem if provided, with defaults.
    '''

    settings = CanarydSettings()

    parser = RawConfigParser()

    try:
        parser.read(config_file)
        canaryd_config_items = parser.items('canaryd')

    except ConfigParserError as e:
        logger.critical('Error in config file ({0}): {1}'.format(config_file, e.message))
        raise ConfigError('Config file error')

    settings.update(dict(canaryd_config_items))
    logger.info('Loaded settings file: {0}'.format(config_file))

    return settings


def write_settings_to_config(settings):
    '''
    Write a config file from settings.
    '''

    # Ensure the config directory exists
    config_directory = get_config_directory()

    if not path.exists(config_directory):
        makedirs(config_directory)

    # Generate the config
    config = RawConfigParser()
    config_file = get_config_file()

    # Attempt to work alongside any existing config
    try:
        config.read(config_file)

    except ConfigParserError as e:
        logger.critical('Error in config file ({0}): {1}'.format(config_file, e.message))

    try:
        config.add_section('canaryd')
    except DuplicateSectionError:
        pass

    for key, value in six.iteritems(settings.__dict__):
        config.set('canaryd', key, value)

    # Write the config file
    config_file = get_config_file()

    with open(config_file, 'wb') as f:
        config.write(f)
