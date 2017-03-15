# canaryd
# File: canaryd/util.py
# Desc: shared utilities for canaryd, mostly for plugins

import logging
import sys
import traceback

from canaryd.packages import click
from canaryd.packages import six

STDOUT_LOG_LEVELS = (logging.DEBUG, logging.INFO)
STDERR_LOG_LEVELS = (logging.WARNING, logging.ERROR, logging.CRITICAL)

# Get the logger
logger = logging.getLogger('canaryd')


class LogFilter(logging.Filter):
    def __init__(self, *levels):
        self.levels = levels

    def filter(self, record):
        return record.levelno in self.levels


class LogFormatter(logging.Formatter):
    level_to_format = {
        logging.DEBUG: lambda s: click.style(s, 'green'),
        logging.WARNING: lambda s: click.style(s, 'yellow'),
        logging.ERROR: lambda s: click.style(s, 'red'),
        logging.CRITICAL: lambda s: click.style(s, 'red', bold=True),
    }

    def format(self, record):
        message = record.msg

        if record.args:
            message = record.msg % record.args

        # We only handle strings here
        if isinstance(message, six.string_types):
            if record.levelno in self.level_to_format:
                message = self.level_to_format[record.levelno](message)

            return '{0} {1}'.format(record.levelname, message)

        # If not a string, pass to standard Formatter
        else:
            return super(LogFormatter, self).format(record)


def setup_logging(verbosity):
    # Figure out the log level
    log_level = logging.CRITICAL

    if verbosity >= 3:
        log_level = logging.DEBUG

    elif verbosity == 2:
        log_level = logging.INFO

    if verbosity == 1:
        log_level = logging.WARNING

    # Set the log level
    logger.setLevel(log_level)

    # Setup a new handler for stdout & stderr
    stdout_handler = logging.StreamHandler(sys.stdout)
    stderr_handler = logging.StreamHandler(sys.stderr)

    # Setup filters to push different levels to different streams
    stdout_filter = LogFilter(*STDOUT_LOG_LEVELS)
    stdout_handler.addFilter(stdout_filter)

    stderr_filter = LogFilter(*STDERR_LOG_LEVELS)
    stderr_handler.addFilter(stderr_filter)

    # Setup a formatter
    formatter = LogFormatter()
    stdout_handler.setFormatter(formatter)
    stderr_handler.setFormatter(formatter)

    # Add the handlers
    logger.addHandler(stdout_handler)
    logger.addHandler(stderr_handler)

    logger.debug('Log level set to: {0}'.format(
        logging.getLevelName(log_level),
    ))


def setup_file_logging(filename):
    handler = logging.FileHandler(filename)
    logger.addHandler(handler)


def print_exception():
    if logger.level != logging.DEBUG:
        return

    # Dev mode, so lets dump as much data as we have
    traceback.print_exc()
