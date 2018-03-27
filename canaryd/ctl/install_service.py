from distutils.spawn import find_executable
from os import path
from pkgutil import get_data

from canaryd_packages import click


def write_script(script_path, script):
    # get_data returns binary, so make it a string
    script = script.decode('utf-8')

    # Swap in the location of canaryd
    canaryd_location = find_executable('canaryd')
    script = script.replace('CANARYD_LOCATION', canaryd_location)

    # Write the init system script
    with open(script_path, 'w') as file:
        file.write(script)


def install_service():
    script = None
    script_path = None
    start_command = None
    enable_command = None

    # OSX/Darwin
    if find_executable('launchctl'):
        script = get_data('canaryd', path.join('init_scripts', 'com.oxygem.canaryd.plist'))
        script_path = path.join('/', 'Library', 'LaunchDaemons', 'com.oxygem.canaryd.plist')
        start_command = 'launchctl load {0}'.format(script_path)
        enable_command = 'launchctl enable system/com.oxygem.canaryd'

    # Systemd
    elif find_executable('systemctl'):
        script = get_data('canaryd', path.join('init_scripts', 'canaryd.service'))
        script_path = path.join('/', 'etc', 'systemd', 'system', 'canaryd.service')
        start_command = 'systemctl start canaryd.service'
        enable_command = 'systemctl enable canaryd.service'

    # Upstart
    elif find_executable('initctl'):
        script = get_data('canaryd', path.join('init_scripts', 'canaryd.conf'))
        script_path = path.join('/', 'etc', 'init', 'canaryd.conf')
        start_command = 'initctl start canaryd'

    # Init.d
    elif path.exists(path.join('/', 'etc', 'init.d')):
        script = get_data('canaryd', path.join('init_scripts', 'canaryd.sh'))
        script_path = path.join('/', 'etc', 'init.d', 'canaryd')
        start_command = 'chmod +x /etc/init.d/canaryd && /etc/init.d/canaryd start'

        if find_executable('update-rc.d'):
            enable_command = 'update-rc.d canaryd defaults'

        elif find_executable('chkconfig'):
            enable_command = 'chkconfig canaryd on'

    write_script(script_path, script)
    click.echo('--> {0} written'.format(script_path))

    return start_command, enable_command
