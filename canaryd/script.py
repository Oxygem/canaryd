from os import listdir, path

from canaryd.settings import get_scripts_directory


def get_scripts(settings):
    available_scripts = listdir(path.join(get_scripts_directory(), 'available'))
    enabled_scripts = listdir(path.join(get_scripts_directory(), 'enabled'))

    all_scripts = set(available_scripts + enabled_scripts)

    return (
        (script, script in enabled_scripts)
        for script in all_scripts
    )
