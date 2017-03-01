import re

from canaryd.plugin import Plugin

USER_REGEX = r'^uid=[0-9]+\(([a-zA-Z0-9_\.\-]+)\) gid=[0-9]+\(([a-zA-Z0-9_\.\-]+)\) groups=([a-zA-Z0-9_\.\-,\(\)\s]+) (.*)$'  # noqa
GROUP_REGEX = r'^[0-9]+\(([a-zA-Z0-9_\.\-]+)\)$'


class Users(Plugin):
    spec = ('user', {
        'group': str,
        'groups': set((str,)),
        'home': str,
        'shell': str,
    })

    command = '''
        for i in `cat /etc/passwd | cut -d: -f1`; do
            ID=`id $i`
            META=`cat /etc/passwd | grep ^$i: | cut -d: -f6-7`
            echo "$ID $META"
        done
    '''

    @staticmethod
    def parse(output):
        users = {}

        for line in output.splitlines():
                matches = re.match(USER_REGEX, line)

                if matches:
                    # Parse out the home/shell
                    home_shell = matches.group(4)
                    home = shell = None

                    # /blah: is just a home
                    if home_shell.endswith(':'):
                        home = home_shell[:1]

                    # :/blah is just a shell
                    elif home_shell.startswith(':'):
                        shell = home_shell[1:]

                    # Both home & shell
                    elif ':' in home_shell:
                        home, shell = home_shell.split(':')

                    # Main user group
                    group = matches.group(2)

                    # Parse the groups
                    groups = []
                    for group_matches in matches.group(3).split(','):
                        name = re.match(GROUP_REGEX, group_matches.strip())
                        if name:
                            name = name.group(1)
                        else:
                            continue

                        # We only want secondary groups here
                        if name != group:
                            groups.append(name)

                    groups = set(groups)

                    users[matches.group(1)] = {
                        'group': group,
                        'groups': groups,
                        'home': home,
                        'shell': shell,
                    }

        return users
