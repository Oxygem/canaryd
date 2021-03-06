from canaryd_packages import click

from canaryd.exceptions import CanarydError
from canaryd.script import (
    copy_builtin_scripts,
    disable_script,
    enable_script,
    get_scripts,
    NoScriptChangesError,
    NoScriptFoundError,
    ScriptNotLinkError,
)
from canaryd.settings import (
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

    for name, enabled, settings in scripts:
        click.echo('    {0}, enabled: {1}, settings: {2}'.format(
            click.style(name, bold=True),
            enabled,
            settings,
        ))


@scripts.command()
@click.option('--no-enable', is_flag=True, default=False)
def install(no_enable=False):
    '''
    Install the builtin scripts and enable where possible.
    '''

    copied, enabled = copy_builtin_scripts(enable_where_possible=not no_enable)
    click.echo('--> Installed {0}, enabled {1}'.format(
        ', '.join(click.style(s, bold=True) for s in copied),
        ', '.join(click.style(s, bold=True) for s in enabled),
    ))


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
