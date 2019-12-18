from __future__ import division

import re
import sys

from multiprocessing import cpu_count
from os import path, sep as os_sep

from canaryd_packages import six

from canaryd.subprocess import get_command_output


def get_ps_cpu_stats():
    '''
    Uses ps + awk to total CPU usage, then divide by # CPUs to get the final %.
    '''

    output = get_command_output(
        "ps -A -o %cpu | awk '{s+=$1} END {print s}'",
        shell=True,
    )

    try:
        cpu_percentage = float(output.strip())

    except (TypeError, ValueError):
        return {}

    return {
        'cpu': {
            'percentage': cpu_percentage / cpu_count(),
        },
    }


def get_proc_cpu_stats():
    '''
    Getsa + parses 2x `/proc/stat` output to calculate CPU %.
    '''

    output = get_command_output(
        'cat /proc/stat && sleep 1 && cat /proc/stat',
        shell=True,
    )

    # Parse /proc/stat
    columns = ('user', 'nice', 'system', 'idle', 'iowait', 'irq', 'soft_irq')
    cpus = {}
    diffs = None
    total = None

    for line in output.splitlines():
        if not line:
            continue

        bits = line.split()
        key, details = bits[0], [int(bit) for bit in bits[1:8]]

        if key != 'cpu':
            continue

        if key in cpus:
            # Calculate usage (second cat)
            diffs = dict(
                (column, details[i] - cpus[key][i])
                for i, column in enumerate(columns)
            )
            total = sum(six.itervalues(diffs))

        else:
            # Set details (first cat)
            cpus[key] = details

    idle_and_iowait = diffs['idle'] + diffs['iowait']

    return {
        'cpu': {
            'current_value': total - idle_and_iowait,
            'current_max': total,
            'percentage': (total - idle_and_iowait) / total * 100,
        },
        'iowait': {
            'current_value': diffs['iowait'],
            'current_max': total,
            'percentage': diffs['iowait'] / total * 100
        },
    }


def get_cpu_stats():
    # If `ps` command used instead of preferred /proc/stat, quickly work
    # out the CPU % and use that (no iowait support).
    if not path.exists('/proc'):
        return get_ps_cpu_stats()

    # Parse /proc/stat
    return get_proc_cpu_stats()


def parse_memory_stats(
    lines,
    value_is_last=False,
    value_multiplier=1,
    value_divisor=1,
):
    key_map = {
        'MemTotal:': 'memory_total',
        'MemFree:': 'memory_free',
        'Buffers:': 'memory_free',
        'Cached:': 'memory_free',
        'SReclaimable:': 'memory_free',
        'Shmem:': 'memory_free',

        'SwapTotal:': 'swap_total',
        'SwapFree:': 'swap_free',
        'SwapCached:': 'swap_free',

        'Pages free:': 'memory_free',
        'Pages inactive:': 'memory_free',
    }

    stats = {}

    for line in lines:
        bits = line.split()

        if value_is_last:
            key = ' '.join(bits[:-1])
            value = bits[-1][:-1]
        else:
            key, value = bits[:2]

        if key in key_map:
            value = int(value) * value_multiplier / value_divisor

            if key_map[key] in stats:
                stats[key_map[key]] += value
                continue

            stats[key_map[key]] = value

    return stats


def get_proc_memory_stats():
    '''
    Gets + parses `/proc/meminfo` output.
    '''

    output = get_command_output(
        'cat /proc/meminfo',
    )

    stats = parse_memory_stats(
        output.splitlines(),
        value_divisor=1024,
    )

    data = {
        'memory': {
            'current_value': int(stats['memory_total'] - stats['memory_free']),
            'current_max': int(stats['memory_total']),
            'percentage': round(
                (stats['memory_total'] - stats['memory_free']) / stats['memory_total'] * 100,
                2,
            ),
        },
    }

    if stats['swap_total'] > 0:
        data['swap'] = {
            'current_value': int(stats['swap_total'] - stats['swap_free']),
            'current_max': int(stats['swap_total']),
            'percentage': round(
                (stats['swap_total'] - stats['swap_free']) / stats['swap_total'] * 100,
                2,
            ),
        }

    return data


def get_vm_stat_memory_stats():
    output = get_command_output(
        'sysctl hw.memsize',
    )

    bits = output.split()
    total_memory = int(bits[1]) / 1024 / 1024

    output = get_command_output(
        'vm_stat',
    )

    stats = parse_memory_stats(
        output.splitlines(),
        value_is_last=True,
        value_multiplier=4096,
        value_divisor=1024 * 1024,
    )

    return {
        'memory': {
            'current_value': int(total_memory - stats['memory_free']),
            'current_max': int(total_memory),
            'percentage': round(
                (total_memory - stats['memory_free']) / total_memory * 100,
                2,
            ),
        },
    }


def get_memory_stats():
    # If `ps` command used instead of preferred /proc/stat, quickly work
    # out the CPU % and use that (no iowait support).
    if sys.platform == 'darwin':
        return get_vm_stat_memory_stats()

    # Parse /proc/stat
    return get_proc_memory_stats()


def get_disk_stats():
    '''
    Parses df output.
    '''

    output = get_command_output('df -kP')

    devices = {}

    for line in output.splitlines():
        bits = line.split()
        filesystem = bits[0]

        if not filesystem.startswith('/'):
            continue

        value = int(bits[2])

        available = int(bits[3])
        max_ = int(bits[1])

        percentage_free = round(available / max_ * 100, 2)
        percentage = 100 - percentage_free

        # Loop backwards through the line bits until we find the bit starting
        # with "/". This means we capture the entire mount path, even if it
        # includes spaces, but also prevents us capturing too much (since df
        # output varies between platforms, like macOS).
        mount_bits = []
        # We know the first few are always blocks/size/used/etc
        possible_bits = bits[2:]

        while possible_bits:
            latest_bit = possible_bits.pop()
            mount_bits.insert(0, latest_bit)

            if latest_bit.startswith('/'):
                break

        mount = ' '.join(mount_bits)

        devices[mount] = {
            'percentage': percentage,
            'current_value': int(round(value / 1024)),
            'current_max': int(round(max_ / 1024)),
        }

    return devices


def _get_device_speed(device):
    speed = 0
    speed_file = path.join(os_sep, 'sys', 'class', 'net', device, 'speed')

    if not path.exists(speed_file):
        return

    try:
        with open(speed_file, 'r') as f:
            data = f.read()
    except IOError:
        return

    speed = int(data)

    # Turn mbits -> bytes
    speed = speed * 125000
    return speed


def get_proc_network_stats():
    '''
    Gets + parses 2x `/proc/net/dev` output.
    '''

    output = get_command_output(
        'cat /proc/net/dev && sleep 1 && cat /proc/net/dev',
        shell=True,
    )

    match_device = r'^\s*([a-zA-Z0-9]+):\s+'

    device_stats = {}
    devices = {}

    for line in output.splitlines():
        matches = re.match(match_device, line)
        if not matches:
            continue

        key, bits = matches.group(1), line.split()

        if key == 'lo':
            continue

        in_bytes = int(bits[1])
        out_bytes = int(bits[9])

        if key in device_stats:
            # Calculate speed + percentage if possible (second cat)
            speed = _get_device_speed(key)

            receive_bytes = in_bytes - device_stats[key][0]
            transmit_bytes = out_bytes - device_stats[key][1]

            receive_percentage = 0
            transmit_percentage = 0
            if speed:
                receive_percentage = receive_bytes / speed * 100
                transmit_percentage = transmit_bytes / speed * 100

            devices['{0}_in'.format(key)] = {
                'current_value': receive_bytes,
                'current_max': speed,
                'percentage': receive_percentage,
            }

            devices['{0}_out'.format(key)] = {
                'current_value': transmit_bytes,
                'current_max': speed,
                'percentage': transmit_percentage,
            }
        else:
            # Assign in/out (first cat)
            device_stats[key] = (in_bytes, out_bytes)

    return devices


def get_netstat_network_stats():
    output = get_command_output(
        'netstat -ib && sleep 1 && netstat -ib',
        shell=True,
    )

    lines = output.splitlines()
    headers = lines[0]
    header_to_position = dict(
        (header, i)
        for i, header in enumerate(headers.split())
    )

    # Collect the metrics from each loop
    first_device_stats = {}
    second_device_stats = {}
    loop_target = first_device_stats

    for line in lines[1:]:
        # Move onto second loop - we store separately as interfaces might be
        # duplicated in the output, and we only want to count their bytes once.
        if line == headers:
            loop_target = second_device_stats
            continue

        bits = line.split()
        key = bits[header_to_position['Name']]

        if key == 'lo0':
            continue

        network = bits[header_to_position['Network']]
        if '<Link' in network:
            continue

        in_bytes = int(bits[header_to_position['Ibytes']])
        out_bytes = int(bits[header_to_position['Obytes']])

        loop_target[key] = (in_bytes, out_bytes)

    # Now loop back and calculate speeds over the 1s
    devices = {}

    for key, stats in second_device_stats.items():
        in_bytes, out_bytes = stats

        receive_bytes = in_bytes - first_device_stats[key][0]
        transmit_bytes = out_bytes - first_device_stats[key][1]

        devices['{0}_in'.format(key)] = {
            'current_value': receive_bytes,
            'percentage': 0.0,
        }

        devices['{0}_out'.format(key)] = {
            'current_value': transmit_bytes,
            'percentage': 0.0,
        }

    return devices


def get_network_stats():
    if path.exists('/proc'):
        return get_proc_network_stats()
    return get_netstat_network_stats()
