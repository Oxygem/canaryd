from os import path
from pkgutil import get_data
from subprocess import CalledProcessError, PIPE

from canaryd.packages import click
from canaryd.packages.check_output import check_output


def which(command):
    try:
        return check_output(
            ('which', command),
            stderr=PIPE,
        ).strip()

    except (CalledProcessError, OSError):
        pass


def write_script(script_path, script):
    canaryd_location = which('canaryd')

    script = script.replace('CANARYD_LOCATION', canaryd_location)

    # Write the init system script
    with open(script_path, 'w') as file:
        file.write(script)


def install_service():
    script = None
    script_path = None
    start_command = None

    # OSX/Darwin
    if which('launchctl'):
        script = get_data('canaryd', path.join('init_scripts', 'canaryd.plist'))
        script_path = path.join('/', 'Library', 'LaunchDaemons', 'canaryd.plist')
        start_command = 'launchctl load {0}'.format(script_path)

    # Systemd
    elif which('systemctl'):
        script = get_data('canaryd', path.join('init_scripts', 'canaryd.service'))
        script_path = path.join('/', 'etc', 'systemd', 'system', 'canaryd.service')
        start_command = 'systemctl start canaryd.service'

    # Upstart
    elif which('initctl'):
        script = get_data('canaryd', path.join('init_scripts', 'canaryd.conf'))
        script_path = path.join('/', 'etc', 'init', 'canaryd.conf')
        start_command = 'start canaryd'

    # Init.d
    elif path.exists(path.join('/', 'etc', 'init.d')):
        script = get_data('canaryd', path.join('init_scripts', 'canaryd.sh'))
        script_path = path.join('/', 'etc', 'init.d', 'canaryd')
        start_command = 'chmod +x /etc/init.d/canaryd && /etc/init.d/canaryd start'

    if any(item is None for item in (script, script_path, start_command)):
        pass

    write_script(script_path, script)
    click.echo('--> {0} written'.format(script_path))

    return start_command
