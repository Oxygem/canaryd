#!/usr/bin/env python

import sys

from os import path


# If /proc/mdstat doesn't exist this script has nothing to check!
if not path.exists('/proc/mdstat'):
    print('No /proc/mdstat found!')
    sys.exit(1)

# Load /proc/mdstat
with open('/proc/mdstat', 'r') as f:
    mdadm_data = f.read()


warnings = []
criticals = []

device = None


for line in mdadm_data.splitlines():
    if not line:
        continue

    if not line.startswith(' '):
        bits = line.split()
        device = bits[0]

        # Handle failed drives in the definition line
        for bit in bits:
            if bit.endswith('(F)'):
                criticals.append((
                    'RAID device {0} has a failed drive: {1}'
                ).format(device, bit))

    # Handle the second line of a device
    if device and 'blocks' in line:
        device_counts = line.split()[-2][1:-1]
        wanted_devices, devices = device_counts.split('/')

        if wanted_devices != devices:
            criticals.append((
                'RAID device {0} is missing devices: {1}/{2}'
            ).format(device, devices, wanted_devices))


exit_code = 0

if warnings:
    exit_code = 1
    print('\n'.join(warnings))

if criticals:
    exit_code = 2
    print('\n'.join(criticals))

if exit_code == 0:
    print('All RAID devices healthy')


sys.exit(exit_code)
