from distutils.spawn import find_executable
from os import access, listdir, makedirs, path, remove, symlink, X_OK
from shutil import copy

from canaryd.log import logger
from canaryd.settings import get_scripts_directory

INVALID_EXTENSIONS = (
    '.pyc',
)

SCRIPT_SETTING_KEYS = {
    'INTERVAL': int,
}


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


def _extract_script_settings(full_path):
    settings = {}

    with open(full_path) as f:
        for line in f.readlines():
            for key, parser in SCRIPT_SETTING_KEYS.items():
                match_key = '# CANARYD_{0}'.format(key)
                if not line.startswith(match_key) or '=' not in line:
                    continue

                _, value = line.split('=', 1)
                value = value.strip()
                value = parser(value)

                if value:
                    settings[key] = value

    return settings


def _get_scripts(dirname):
    scripts = []
    all_settings = {}

    script_names = listdir(dirname)
    for name in script_names:
        if any(name.endswith(e) for e in INVALID_EXTENSIONS):
            continue

        full_path = path.join(dirname, name)
        if not access(full_path, X_OK):
            continue

        scripts.append(name)
        settings = _extract_script_settings(full_path)
        if settings:
            all_settings[name] = settings

    return scripts, all_settings


def get_scripts(settings):
    script_settings = {}

    available_scripts, available_script_settings = _get_scripts(
        path.join(get_scripts_directory(), 'available'),
    )
    script_settings.update(available_script_settings)

    enabled_scripts, enabled_script_settings = _get_scripts(
        path.join(get_scripts_directory(), 'enabled'),
    )
    script_settings.update(enabled_script_settings)

    all_scripts = set(available_scripts + enabled_scripts)

    return (
        (script, script in enabled_scripts, script_settings.get(script))
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
