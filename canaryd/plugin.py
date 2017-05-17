# canaryd
# File: canaryd/plugin.py
# Desc: functions for handling the various built in state gathering plugins

import re

from glob import glob
from os import path
from subprocess import CalledProcessError

from canaryd.packages import six
from canaryd.packages.check_output import check_output
from canaryd.packages.importlib import import_module

from canaryd.log import logger, print_exception # noqa

PLUGINS = []
NAME_TO_PLUGIN = {}


def underscore(name):
    '''
    Transform CamelCase -> snake_case.
    '''

    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


class NoPluginError(Exception):
    pass


class PluginMeta(type):
    def __init__(cls, name, bases, attrs):
        if name == 'Plugin':
            return

        name = underscore(name)

        plugin_instance = cls()
        plugin_instance.name = name

        PLUGINS.append(plugin_instance)
        NAME_TO_PLUGIN[name] = plugin_instance


@six.add_metaclass(PluginMeta)
class Plugin(object):
    diff_updates = True

    class PrepareError(Exception):
        pass

    @staticmethod
    def is_change(key, previous_item, item):
        return True

    @staticmethod
    def cleanup():
        pass

    def get_state(self, settings):
        data = check_output(
            self.command,
            shell=True,
        )

        return self.parse(data)

    def prepare(self, settings):
        check_output(
            getattr(self, 'prepare_command', self.command),
            shell=True,
        )

    def log(self, message):
        message = '[{0}]: {1}'.format(self.name, message)
        logger.debug(message)

    def check_spec_key(self, key, value):
        spec = self.spec[1]

        if key not in spec:
            raise ValueError(
                'Key not found in plugin {0} spec: {1} (value = {2})'.format(
                    self.name,
                    key,
                    value,
                ),
            )

    # Serialisation
    #

    def serialise_value(self, key, value):
        spec = self.spec[1]
        self.check_spec_key(key, value)

        if isinstance(spec[key], set) and isinstance(value, set):
            return list(value)

        return value

    def serialise_item(self, item):
        return dict(
            (key, self.serialise_value(key, value))
            for key, value in six.iteritems(item)
        )

    def serialise_state(self, state):
        return dict(
            (key, self.serialise_item(item))
            for key, item in six.iteritems(state)
        )

    def serialise_changes(self, changes):
        return dict(
            (key, (self.serialise_value(key, item[0]), self.serialise_value(key, item[1])))
            for key, item in six.iteritems(changes)
        )

    # Unserialisation
    #

    def unserialise_value(self, key, value):
        spec = self.spec[1]
        self.check_spec_key(key, value)

        if isinstance(spec[key], set):
            return set(value)

        return value

    def unserialise_item(self, item):
        return dict(
            (key, self.unserialise_value(key, value))
            for key, value in six.iteritems(item)
        )

    def unserialise_state(self, items):
        return dict(
            (key, self.unserialise_item(item))
            for key, item in six.iteritems(items)
        )


def get_plugins():
    '''
    Get the list of installed plugins.
    '''

    module_filenames = glob(path.join(path.dirname(__file__), 'plugins', '*.py'))

    module_names = [
        path.basename(name)[:-3]
        for name in module_filenames
        if not name.endswith('__init__.py')
    ]

    # Import all the modules to populate PLUGINS
    for name in module_names:
        import_module('canaryd.plugins.{0}'.format(name))

    return PLUGINS


def get_plugin_names():
    return six.iterkeys(NAME_TO_PLUGIN)


def get_plugin_by_name(plugin_name):
    if plugin_name not in NAME_TO_PLUGIN:
        raise NoPluginError('Missing plugin: {0}'.format(plugin_name))

    return NAME_TO_PLUGIN[plugin_name]


def prepare_plugin(plugin, settings):
    logger.debug('Preparing plugin: {0}'.format(plugin))

    try:
        plugin.prepare(settings)

    except Plugin.PrepareError as e:
        logger.info('Plugin prepare failed: {0}: {1}'.format(
            plugin.name, e.message,
        ))
        print_exception(debug_only=True)
        return False, e

    except (CalledProcessError, OSError) as e:
        logger.info('Plugin command missing/failed: {0}'.format(
            plugin.name,
        ))
        print_exception(debug_only=True)
        return False, e

    except Exception as e:
        logger.warning('Error preparing plugin: {0}: {1}'.format(
            plugin.name,
            e,
        ))
        print_exception()
        return False, e

    return True


def get_and_prepare_working_plugins(settings):
    logger.info('Loading plugins...')

    all_plugins = get_plugins()
    working_plugins = []

    for plugin in all_plugins:
        status = prepare_plugin(plugin, settings)

        if status is True:
            working_plugins.append(plugin)

    logger.info('Loaded plugins: {0}'.format(', '.join([
        plugin.__class__.__name__
        for plugin in working_plugins
    ])))

    return working_plugins


def cleanup_plugins(plugins):
    for plugin in plugins:
        try:
            plugin.cleanup()

        except Exception as e:
            logger.warning(
                'Error cleaning plugin: {0}: {1}'.format(plugin.name, e),
            )
            print_exception()
            return False, e


def get_plugin_state(plugin, settings):
    '''
    Gets state output from a single plugin.
    '''

    logger.debug('Running plugin: {0}'.format(plugin))

    try:
        state = plugin.get_state(settings)

    except Exception as e:
        logger.warning('Error running plugin: {0}: {1}'.format(plugin, e))
        print_exception()
        return False, e

    if not isinstance(state, (dict, list)):
        return False, TypeError('Invalid state type: {0}'.format(state))

    return True, state


def get_plugin_states(plugins, settings):
    '''
    Gets state output from multiple plugins.
    '''

    return [
        (plugin, get_plugin_state(plugin, settings))
        for plugin in plugins
    ]
