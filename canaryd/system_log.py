from collections import defaultdict
from distutils.spawn import find_executable
from os import path
from threading import Thread

from canaryd_packages.six.moves.queue import Queue

from canaryd.subprocess import ensure_command_tuple, PIPE, Popen, STDOUT

POSSIBLE_SYSLOG_FILENAMES = (
    '/var/log/syslog',  # Debian
    '/var/log/messages',  # Red Hat
    '/var/log/system.log',  # MacOS
)


def _enqueue_command_output(command, queue):
    process = Popen(command, stdout=PIPE, stderr=STDOUT)
    while True:
        line = process.stdout.readline()
        queue.put(line)


def _get_enqueue_thread(command, queue):
    command = ensure_command_tuple(command)
    thread = Thread(
        target=_enqueue_command_output,
        args=(command, queue),
    )
    thread.daemon = True
    thread.start()
    return thread


def get_journal_feed_thread(queue):
    return _get_enqueue_thread('journalctl -f', queue)


def get_syslog_feed_thread(queue):
    for filename in POSSIBLE_SYSLOG_FILENAMES:
        if path.exists(filename):
            return _get_enqueue_thread('tail -F {0}'.format(filename), queue)


def parse_journal_line(line):
    pass


def parse_syslog_line(line):
    pass


class _SystemLog(object):
    '''
    A class that follows system logs (via journald or syslog) and captures interesting
    logs as requested by plugins. Ie the services plugin might request this instance
    to collect all mysqld logs.

    By default will not collect any log lines only parse and throw out.
    '''

    def __init__(self):
        self.logs = defaultdict(list)
        self.interested_logs = set()
        self.feed = Queue()

        self.init_feed()

    def init_feed(self):
        if find_executable('journalctl'):
            self.feed_thread = get_journal_feed_thread(self.feed)
            self.feed_line_parser = parse_journal_line
        else:
            self.feed_thread = get_syslog_feed_thread(self.feed)
            self.feed_line_parser = parse_syslog_line

    def check_feed_alive(self):
        if not self.feed_thread.is_alive():
            self.init_feed()

    def process_feed(self):
        if not self.feed_thread:
            return

        self.check_feed_alive()

        while True:
            try:
                line = self.feed.get_nowait()
            except self.feed.Empty:
                break
            else:
                data = self.feed_line_parser(line)
                if data['name'] in self.interested_logs:
                    self.logs[data['name']] = data['line']

    def start_collecting_log(self, log_name):
        '''
        Start collecting logs where the name matches the provided log name.


        Args:
            log_name (str): name of the logs to start capturing
        '''

        self.interested_logs.add(log_name)

    def get_any_logs(self, log_name):
        '''
        Get any logs for a given name.


        Args:
            log_name (str): name of the logs to start capturing

        Raises:
            ValueError: when not capturing logs matching the given ``log_name``
        '''

        if log_name not in self.interested_logs:
            raise ValueError('Not capturing logs for {0}'.format(log_name))

        self.process_feed()  # process any pending logs first

        # Now pop out any logs matching this log name, ignoring if not present
        logs = self.logs.pop(log_name, [])
        return logs


# Expose the system logger for import, we only ever want one instance of this!
system_log = _SystemLog()


class Tailer(object):
    '''
    Small class to follow lines output from a file *after initialisation*.
    '''

    def __init__(self, filename):
        self.filename = filename
        self.modified = path.getmtime(filename)
        self.offset = path.getsize(filename)

    def read_lines(self):
        modified = path.getmtime(self.filename)
        if modified == self.modified:
            return []

        with open(self.filename, 'r') as f:
            f.seek(self.offset)
            data = f.read()

        self.modified = modified
        self.offset = path.getsize(self.filename)

        return list(filter(None, data.split('\n')))
