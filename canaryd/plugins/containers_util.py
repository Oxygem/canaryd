import json

from canaryd.packages.check_output import CalledProcessError, check_output


def get_docker_containers():
    containers = {}

    try:
        output = check_output(
            'docker inspect `docker ps -qa`',
            shell=True,
        )

    # Either Docker is down or there are no containers
    except CalledProcessError:
        return containers

    data = json.loads(output)

    for container in data:
        container_data = {
            'runtime': 'docker',
            'running': container['State']['Running'],
            'command': ' '.join(container['Config']['Cmd']),
            'environment': container['Config']['Env'],
            'image': container['Config']['Image'],
            'id': container['Id'],
        }

        # Figure out the name(s)
        if 'Names' in container:
            container_data['names'] = container['Names']

        elif 'Name' in container:
            container_data['names'] = [container['Name']]

        # If running, get the PID
        if container_data['running']:
            container_data['pid'] = container['State']['Pid']

        container_key = 'docker/{0}'.format(container_data['names'][0])
        containers[container_key] = container_data

    return containers


def get_lxc_containers():
    output = check_output(
        'lxc list --fast --format json',
        shell=True,
    )

    containers = {}

    data = json.loads(output)

    for container in data:
        container_data = {
            'runtime': 'lxc',
            'running': container['status'] == 'Running',
        }

        container_key = 'lxc/{0}'.format(container['name'])
        containers[container_key] = container_data

    return containers
