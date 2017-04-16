from os import listdir, path

from canaryd.settings import get_config_directory


def get_scripts_directory():
    return path.join(get_config_directory(), 'scripts')


def get_scripts(settings):
    available_scripts = listdir(path.join(get_scripts_directory(), 'available'))
    enabled_scripts = listdir(path.join(get_scripts_directory(), 'enabled'))

    all_scripts = list(set(available_scripts + enabled_scripts))

    return (
        (script, script in enabled_scripts)
        for script in all_scripts
    )
