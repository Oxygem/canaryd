from canaryd.packages import click  # noqa

from canaryd.exceptions import CanarydError
from canaryd.script import (
    disable_script,
    enable_script,
    get_scripts,
    NoScriptChangesError,
    NoScriptFoundError,
    ScriptNotLinkError,
)
from canaryd.settings import (
    copy_builtin_scripts,
    get_settings,
)

from . import main


@main.group(invoke_without_command=True)
@click.pass_context
def scripts(ctx):
    '''
    List and manage scripts for canaryd.

    \b
    # List scripts
    canaryctl scripts

    \b
    # Enable a script
    canaryctl scripts enable <script.sh>

    \b
    # Disable a script
    canaryctl scripts disable <script.sh>
    '''

    if ctx.invoked_subcommand is not None:
        return

    scripts = get_scripts(get_settings())

    click.echo('--> Scripts:')

    for script in scripts:
        click.echo('    {0}, enabled: {1}'.format(
            click.style(script[0], bold=True),
            script[1],
        ))


@scripts.command()
def copy():
    '''
    Copy the builtin scripts into the servers canaryd settings directory.
    '''

    copy_builtin_scripts()


@scripts.command()
@click.argument('script')
def enable(script):
    '''
    Enable a script.
    '''

    try:
        enable_script(script)

    except NoScriptFoundError as e:
        raise CanarydError(click.style(
            'No script file ({0}) exists.'.format(e.message),
            'red',
        ))

    except NoScriptChangesError:
        click.echo('Script {0} is already enabled.'.format(
            click.style(script, bold=True),
        ))
        return

    click.echo('Script enabled: {0}'.format(click.style(script, bold=True)))


@scripts.command()
@click.argument('script')
def disable(script):
    '''
    Disable a script.
    '''

    try:
        disable_script(script)

    except NoScriptFoundError as e:
        raise CanarydError(click.style(
            'No script file ({0}) exists.'.format(e.message),
            'red',
        ))

    except ScriptNotLinkError as e:
        raise CanarydError(click.style(e.message, 'yellow'))

    except NoScriptChangesError:
        click.echo('Script {0} is already disabled.'.format(
            click.style(script, bold=True),
        ))
        return

    click.echo('Script disabled: {0}'.format(click.style(script, bold=True)))
