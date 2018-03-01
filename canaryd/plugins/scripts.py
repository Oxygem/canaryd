from os import path

from canaryd.packages import six
from canaryd.packages.six.moves import shlex_quote

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
        canaryctl script enable FILENAME
        canaryctl script disable FILENAME

        # Create a new script
        canaryctl script create FILENAME

        # List all scripts (available and enabled)
        canaryctl scripts
    '''

    spec = ('script', {
        'output': six.text_type,
        'exit_code': int,
    })

    # Don't generate events from state updates (see generate_issues_from_key_change below)
    generate_update_events = False

    def prepare(self, settings):
        pass

    def get_state(self, settings):
        scripts = [
            (script, path.join(get_scripts_directory(), 'enabled', script))
            for script, enabled in get_scripts(settings)
            if enabled
        ]

        results = {}

        for script, script_path in scripts:
            try:
                output = get_command_output(
                    shlex_quote(script_path),
                )

                results[script] = {
                    'output': output.strip(),
                    'exit_code': 0,
                }

            except (CalledProcessError, OSError) as e:
                results[script] = {
                    'output': e.output.strip(),
                    'exit_code': e.returncode,
                }

        return results

    @staticmethod
    def generate_issues_from_key_change(event_type, key, data_changes, settings):
        # If the script has been removed, resolve any leftover issues and exit.
        # (the delete event is still created).
        if event_type == 'deleted':
            yield 'resolved', None, None
            return

        if 'exit_code' in data_changes:
            _, to_code = data_changes['exit_code']

            message = None
            data = data_changes

            if 'output' in data_changes:
                data = dict(
                    (k, v)
                    for k, v in six.iteritems(data_changes)
                    if k != 'output'
                )
                message = data_changes['output'][1]

            if to_code >= 2:
                yield 'critical', message, data

            elif to_code == 1:
                yield 'warning', message, data

            elif to_code == 0:
                # Include all the changes - including output
                yield 'resolved', message, data_changes
