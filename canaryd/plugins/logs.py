from os import path

from canaryd_packages import six
from canaryd_packages.six.moves.queue import Empty

from canaryd.plugin import Plugin

from .logs_util import (
    follow_command_output,
    parse_auth_logs,
    parse_dmesg_logs,
    parse_lynis_logs,
    parse_system_logs,
    tail_and_follow_file,
)

FILENAME_TO_PARSER = {
    # System logs - ANY POINT?!
    '/var/log/messages': parse_system_logs,
    '/var/log/syslog': parse_system_logs,
    '/var/log/system.log': parse_system_logs,

    # Capture failed logins
    '/var/log/auth.log': parse_auth_logs,
    '/var/log/secure': parse_auth_logs,

    # Application specific
    '/var/log/lynis.log': parse_lynis_logs,
}

COMMAND_TO_PARSER = {
    'dmesg -w': parse_dmesg_logs,
}


class Logs(Plugin):
    '''
    Watches system log files and identifies common error patterns.
    '''

    spec = ('filename', {
        'messages': [six.text_type],
    })

    # Don't diff updates - always send the entire state
    diff_updates = False

    # Don't generate any add/update/delete events from state changes
    # see generate_issues_from_change below
    generate_update_events = True
    generate_added_events = True
    generate_deleted_events = True

    initialised = False

    def prepare(self, settings):
        if not self.initialised:
            queues_parsers = []

            for command, parser in COMMAND_TO_PARSER.items():
                queues_parsers.append(
                    (command, follow_command_output(command), parser),
                )

            for filename, parser in FILENAME_TO_PARSER.items():
                if not path.isfile(filename):
                    continue

                queues_parsers.append(
                    (filename, tail_and_follow_file(filename), parser),
                )

            self.queues_parsers = queues_parsers
            self.initialised = True

    def get_state(self, settings):
        file_to_lines = {}

        for filename, queue, parser in self.queues_parsers:
            log_lines = []

            while True:
                try:
                    line = queue.get(block=False)
                except Empty:
                    break

                parsed_line = parser(line)
                if parsed_line:
                    log_lines.append(parsed_line)

            file_to_lines[filename] = {
                'messages': log_lines,
            }
        return file_to_lines

    @staticmethod
    def generate_issues_from_change(change, settings):
        pass
