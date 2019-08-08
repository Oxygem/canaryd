from distutils.spawn import find_executable
from os import listdir, makedirs, path, remove, symlink
from shutil import copy

from canaryd.log import logger
from canaryd.settings import get_scripts_directory

INVALID_EXTENSIONS = (
    '.pyc',
)


class ScriptException(Exception):
    pass


class NoScriptFoundError(ScriptException):
    '''
    Raised when a script file cannot be located.
    '''


class NoScriptChangesError(ScriptException):
    '''
    Raised when no changes are made when enabling/disabling scripts.
    '''


class ScriptNotLinkError(ScriptException):
    '''
    Raised when the script is not a link when disabling scripts.
    '''


def get_scripts(settings):
    available_scripts = listdir(path.join(get_scripts_directory(), 'available'))
    enabled_scripts = listdir(path.join(get_scripts_directory(), 'enabled'))

    all_scripts = set(available_scripts + enabled_scripts)
    all_scripts = filter(
        lambda script: not script.endswith(INVALID_EXTENSIONS),
        all_scripts,
    )

    return (
        (script, script in enabled_scripts)
        for script in all_scripts
    )


def enable_script(script, raise_if_noop=True):
    scripts_directory = get_scripts_directory()

    source_script = path.join(scripts_directory, 'available', script)
    link_name = path.join(scripts_directory, 'enabled', script)

    if not path.exists(source_script):
        raise NoScriptFoundError(source_script)

    if path.exists(link_name):
        if not raise_if_noop:
            return
        raise NoScriptChangesError()

    symlink(
        source_script,
        link_name,
    )


def disable_script(script, raise_if_noop=True):
    scripts_directory = get_scripts_directory()

    source_script = path.join(scripts_directory, 'available', script)
    link_name = path.join(scripts_directory, 'enabled', script)

    if not path.exists(source_script):
        raise NoScriptFoundError(source_script)

    if not path.exists(link_name):
        if not raise_if_noop:
            return
        raise NoScriptChangesError()

    if not path.islink(link_name):
        raise ScriptNotLinkError(
            'Script {0} is not a link. You should move it to: {1}.'.format(
                link_name, source_script,
            ),
        )

    remove(link_name)


def ensure_scripts_directory():
    # Make sure the scripts directory exists
    scripts_directory = get_scripts_directory()

    if not path.exists(scripts_directory):
        logger.debug('Creating scripts directory: {0}'.format(scripts_directory))

        # Make the scripts, scripts/enabled & scripts/available directories
        makedirs(path.join(scripts_directory, 'enabled'))
        makedirs(path.join(scripts_directory, 'available'))

        copy_builtin_scripts()


def copy_builtin_scripts(enable_where_possible=True):
    # Copy built in scripts to the scripts/available directory
    available_scripts_directory = path.join(get_scripts_directory(), 'available')

    logger.debug(
        'Copying default scripts to: {0}'.format(available_scripts_directory),
    )

    builtin_scripts_directory = path.join(path.dirname(__file__), 'scripts')

    copied = []
    enabled = []

    for file in listdir(builtin_scripts_directory):
        copy(
            path.join(builtin_scripts_directory, file),
            path.join(available_scripts_directory, file),
        )
        copied.append(file)

    if enable_where_possible:
        script_to_check = {
            'raid_health.py': path.exists('/proc/mdstat'),
            'disk_health.py': find_executable('smartctl'),
        }

        for script, can_enable in script_to_check.items():
            if can_enable:
                enable_script(script, raise_if_noop=False)
                enabled.append(script)

    return copied, enabled
