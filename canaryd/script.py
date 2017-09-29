from os import listdir, path, remove, symlink

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


def enable_script(script):
    scripts_directory = get_scripts_directory()

    source_script = path.join(scripts_directory, 'available', script)
    link_name = path.join(scripts_directory, 'enabled', script)

    if not path.exists(source_script):
        raise NoScriptFoundError(source_script)

    if path.exists(link_name):
        raise NoScriptChangesError()

    symlink(
        source_script,
        link_name,
    )


def disable_script(script):
    scripts_directory = get_scripts_directory()

    source_script = path.join(scripts_directory, 'available', script)
    link_name = path.join(scripts_directory, 'enabled', script)

    if not path.exists(source_script):
        raise NoScriptFoundError(source_script)

    if not path.exists(link_name):
        raise NoScriptChangesError()

    if not path.islink(link_name):
        raise ScriptNotLinkError(
            'Script {0} is not a link. You should move it to: {1}.'.format(
                link_name, source_script,
            ),
        )

    remove(link_name)
