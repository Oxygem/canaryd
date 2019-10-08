# canaryd
# File: canaryd/plugin.py
# Desc: functions for handling the various built in state gathering plugins

from __future__ import division

import re
import traceback

from distutils.spawn import find_executable

from canaryd_packages import six

from canaryd.log import logger, print_exception
from canaryd.subprocess import get_command_output

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
    '''
    The base plugin implementation.
    '''

    #: Whether to diff state changes or always pass the entire state
    diff_updates = True

    #: Whether to generate update events for this plugin
    generate_update_events = True
    #: Whether to generate added events for this plugin
    generate_added_events = True
    #: Whether to generate deleted events for this plugin
    generate_deleted_events = True

    #: Log warnings for missing keys when validating state items?
    warn_for_missing_keys = True

    #: Whether this plugin is considered "slow" and run less often
    is_slow = False

    class PrepareError(Exception):
        '''
        Raised when a plugin cannot be prepared for execution.
        '''

    def __repr__(self):
        return 'Plugin: {0}'.format(self.name)

    @staticmethod
    def get_action_for_change(change):
        '''
        Get the event action for a given change. Executed on the server side on
        receiving state.

        Args:
            change (Change): a change object

        Returns:
            action (str): the event action
        '''

    @staticmethod
    def get_description_for_change(change):
        '''
        Get the event description for a given change. Executed on the server
        side on receiving state.

        Args:
            change (Change): a change object

        Returns:
            description (str): the event description
        '''

    @staticmethod
    def should_apply_change(change):
        '''
        Deterime whether a given change should be applied. Executed on the
        server side on receiving state.

        Args:
            change (Change): a change object

        Returns:
            status (bool): whether the change should be applied
        '''

        return True

    @staticmethod
    def generate_issues_from_change(change, settings):
        '''
        Plugin can generate issue type events from a given change. Executed on
        the server side on receiving state.

        Args:
            change (Change): a change object
            settings (dict): canaryd daemon settings

        Yields:
            events (tuple): ``(event_type, event_message, event_data)``
        '''

    def get_timeout(self, settings):
        # Set an alarm: a plugin can only run for MAX half the interval time
        return int(round(settings.collect_interval_s / 2))

    def log(self, message):
        message = '[{0}]: {1}'.format(self.name, message)
        logger.debug(message)

    def get_events(self, settings):
        '''
        Plugin can generate raw events here, ie for things that don't fit into
        the spec/state model. This should be a generator yielding event tuples:

        Args:
            settings (dict): canaryd daemon settings

        Returns:
            events (list): ``[(event_type, event_message, event_data), ...]``
        '''

        return []

    def get_state(self, settings):
        '''
        Get the current state for this plugin. Returns structured objects that
        match the spec defined on the plugin.

        Args:
            settings (dict): canaryd daemon settings

        Returns:
            state (dict): dictionary of current state items, matching plugin spec
        '''

        data = get_command_output(
            self.command,
            timeout=self.get_timeout(settings),
        )

        return self.parse(data)

    def parse(self, data):
        raise NotImplementedError

    def prepare(self, settings):
        '''
        Determine if this plugin can be executed.

        Args:
            settings (dict): canaryd daemon settings

        Raises:
            Plugin.PrepareError
            OSError
            Exception
        '''

        command_bits = self.command.split()
        command = command_bits[0]

        if not find_executable(command):
            raise OSError('Could not find executable: {0}'.format(command))

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

        wanted_type = spec[key]
        valid = False

        def validate_type(value, wanted_type):
            return (
                # None/null allowed for all keys
                value is None
                # Or the wanted type
                or isinstance(value, wanted_type)
                # If we wan't unicode but got bytes, OK to serialise
                or (
                    wanted_type is six.text_type
                    and isinstance(value, six.binary_type)
                )
            )

        # Any type allowed?
        if wanted_type is None:
            valid = True

        # If the spec is a list - type is/should be the only list item, and our
        # value should be a list of items that match the type.
        elif isinstance(wanted_type, list):
            wanted_type = wanted_type[0]

            if isinstance(value, (list, set, tuple)) and all(
                validate_type(v, wanted_type)
                for v in value
            ):
                valid = True

        elif validate_type(value, wanted_type):
            valid = True

        if not valid:
            raise TypeError((
                'Invalid type for key `{0}` in plugin {1} '
                '(want type = {2}, value type = {3})'
            ).format(key, self.name, wanted_type, type(value)))

    def validate_state(self, state):
        '''
        Validate a given state dict is valid by checking each key/value within
        an item match up with the spec.
        '''

        spec = self.spec[1]
        key_to_missing_count = {}

        for key, item in six.iteritems(state):
            # Check all the keys the item has
            for k, v in six.iteritems(item):
                self.check_spec_key(k, v)

            # Check, but only warn, for keys the item *doesn't* have - this is
            # only because it's useful, plugins are free to submit incomplete
            # items.
            for spec_key in spec.keys():
                if spec_key not in item:
                    key_to_missing_count.setdefault(spec_key, 0)
                    key_to_missing_count[spec_key] += 1

        # Not all plugins expect all keys
        if not self.warn_for_missing_keys:
            return

        for key, missing_count in six.iteritems(key_to_missing_count):
            logger.warning('{0} items for plugin {1} are missing key {2}'.format(
                missing_count,
                self.name,
                key,
            ))


def get_plugins():
    '''
    Get the list of installed plugins.
    '''

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
            plugin.name, e.args,
        ))
        print_exception(debug_only=True)
        return False, e

    except OSError as e:
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


def get_and_prepare_working_plugins(settings, include_slow=True):
    all_plugins = get_plugins()
    working_plugins = []

    for plugin in all_plugins:
        if not include_slow and plugin.is_slow:
            continue

        status = prepare_plugin(plugin, settings)

        if status is True:
            working_plugins.append(plugin)

    logger.info('Loaded plugins: {0}'.format(', '.join([
        plugin.name
        for plugin in working_plugins
    ])))

    return working_plugins


def get_plugin_state(plugin, settings):
    '''
    Gets state output from a single plugin.
    '''

    logger.debug('Running plugin: {0}'.format(plugin))

    status = False
    state = None

    try:
        state = plugin.get_state(settings)
        status = True

    except Exception as e:
        logger.warning('Error running plugin: {0}: {1}'.format(plugin, e))
        print_exception()
        # Attach the tracback to the exception before returning as state
        e._traceback = traceback.format_exc()
        state = e

    # Validate the state
    if status:
        plugin.validate_state(state)

    return status, state


def get_plugin_states(plugins, settings):
    '''
    Gets state output from multiple plugins.
    '''

    return [
        (plugin, get_plugin_state(plugin, settings))
        for plugin in plugins
    ]
