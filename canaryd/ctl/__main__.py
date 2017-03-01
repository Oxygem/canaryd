# canaryd
# File: canaryd/ctl/__main__.py
# Desc: entry point for canaryctl

from __future__ import print_function

from canaryd.packages import click

from canaryd.exceptions import CanarydError
from canaryd.log import logger, setup_logging
from canaryd.remote import ApiError
from canaryd.version import __version__

from . import init_command, register_command, state_command, plugins_command


def _handle_exceptions(func, *args, **kwargs):
    try:
        func(*args, **kwargs)

    except ApiError as e:
        logger.critical('API {0} error: {1}'.format(e.status_code, e.message))

    except CanarydError:
        raise

    except Exception:
        logger.critical('Unexpected exception:')
        raise


# Parse arguments
@click.group()
@click.option('-v', '--verbose', count=True)
def main(verbose=0):
    '''
    canaryd control.
    '''

    # For canaryctl we want warnings to show, so always bump verbosity
    verbose += 1
    setup_logging(verbose)


@main.command()
@click.argument('key', required=False)
def register(key):
    '''
    Register this server on Service Canary.

    If no api key is provided, you can sign up instantly.
    '''

    _handle_exceptions(register_command, key)


@main.command()
@click.option('--start', is_flag=True, default=False)
@click.argument('key', required=False)
def init(start, key):
    '''
    Create the canaryd service and start it.

    This command will attempt to register if the config file is not found.
    '''

    _handle_exceptions(
        init_command,
        key,
        auto_start=start,
    )


@main.command()
@click.argument('plugin')
def state(plugin):
    '''
    Get state for a single plugin.
    '''

    _handle_exceptions(state_command, plugin)


@main.command()
def plugins():
    '''
    List all plugins.
    '''

    _handle_exceptions(plugins_command)


@main.command()
def version():
    '''
    Print the canaryd version.
    '''

    click.echo('canaryd v{0}'.format(__version__))


main()
