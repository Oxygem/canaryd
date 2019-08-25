from os import path

from canaryd_packages import six
from canaryd_packages.six.moves import shlex_quote

from canaryd.plugin import Plugin
from canaryd.script import get_scripts, get_scripts_directory
from canaryd.subprocess import CalledProcessError, get_command_output


class Scripts(Plugin):
    '''
    The scripts plugin executes user enabled scripts.

    Scripts have the following spec (think Sensu/Nagios):

    + Output a message and/or JSON data to stdout or stderr
    + Exit with code:
        * 0 - indicates all OK
        * 1 - indicates a warning
        * 2 - indicates a critical

    Scripts can be added to the canaryd config directory in ``scripts/available``
    and then enabled using ``canaryctl``, eg:

    .. code:: sh

        # Enable/disable scripts in $canaryd-config/scripts/available
        canaryctl scripts enable FILENAME
        canaryctl scripts disable FILENAME

        # List all scripts (available and enabled)
        canaryctl scripts
    '''

    spec = ('script', {
        'output': six.text_type,
        'exit_code': int,
        'enabled': bool,
    })

    # Don't generate events from state updates (see generate_issues_from_change below)
    generate_update_events = False

    def prepare(self, settings):
        pass

    def get_state(self, settings):
        results = {}

        for script, enabled in get_scripts(settings):
            if not enabled:
                results[script] = {
                    'enabled': False,
                }
                continue

            script_path = path.join(get_scripts_directory(), 'enabled', script)

            try:
                output = get_command_output(
                    shlex_quote(script_path),
                )

                results[script] = {
                    'output': output.strip(),
                    'exit_code': 0,
                    'enabled': True,
                }

            except (CalledProcessError, OSError) as e:
                results[script] = {
                    'output': e.output.strip(),
                    'exit_code': e.returncode,
                    'enabled': True,
                }

        return results

    @staticmethod
    def generate_issues_from_change(change, settings):
        data_changes = change.data

        # If the script has been removed, resolve any leftover issues and exit.
        # (the delete event is still created).
        if change.type == 'deleted':
            yield 'resolved', None, None
            return

        # If the script has been disabled on the host, resolve any leftover issues
        # and exit.
        if (
            change.type == 'updated'
            and 'enabled' in data_changes
            and data_changes['enabled'][1] is False
        ):
            yield 'resolved', None, None
            return

        if 'exit_code' in data_changes:
            _, to_code = data_changes['exit_code']

            message = None

            if 'output' in data_changes:
                message = data_changes['output'][1]

            if to_code >= 2:
                yield 'critical', message, data_changes

            elif to_code == 1:
                yield 'warning', message, data_changes

            elif to_code == 0:
                # Include all the changes - including output
                yield 'resolved', message, data_changes
