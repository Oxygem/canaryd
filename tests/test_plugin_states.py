from contextlib import contextmanager
from os import path
from unittest import TestCase

from dictdiffer import diff
from jsontest import JsonTest
from mock import patch

from canaryd_packages import six

from canaryd.plugin import get_plugin_by_name
from canaryd.settings import CanarydSettings


class TestPluginRealStates(TestCase):
    def test_meta_plugin(self):
        plugin = get_plugin_by_name('meta')
        plugin.get_state({})


@six.add_metaclass(JsonTest)
class TestPluginStates(TestCase):
    jsontest_files = path.join('tests/plugins')
    test_settings = CanarydSettings()

    @contextmanager
    def patch_commands(self, commands):
        def handle_command(command, *args, **kwargs):
            command = command[0]

            if command not in commands:
                raise ValueError('Broken tests: {0} not in commands: {1}'.format(
                    command, commands.keys(),
                ))

            return '\n'.join(commands[command])

        check_output_patch = patch(
            'canaryd.subprocess.check_output',
            handle_command,
        )
        check_output_patch.start()

        yield

        check_output_patch.stop()

    def jsontest_function(self, test_name, test_data):
        plugin = get_plugin_by_name(test_data['plugin'])

        with self.patch_commands(test_data['commands']):
            state = plugin.get_state(self.test_settings)

        try:
            self.assertEqual(state, test_data['state'])
        except AssertionError:
            print(list(diff(test_data['state'], state)))
            raise
