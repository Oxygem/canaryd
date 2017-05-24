#!/usr/bin/env python

import sys

from subprocess import CalledProcessError

from canaryd.packages.check_output import check_output


try:
    # Ensure smartctl is present & working
    check_output(
        'smartctl --version',
        shell=True,
    )

except (CalledProcessError, OSError):
    print('No smartctl found!')
    sys.exit(1)


try:
    # Look for OSX disks first (OSX has /dev/sdt which breaks below)
    disks_data = check_output(
        'ls /dev/disk?',
        shell=True,
    )

except (CalledProcessError, OSError):
    # Look for Linux disks (/dev/sdX, /dev/hdX)
    disks_data = check_output(
        'ls /dev/[hs]d?',
        shell=True,
    )


# Turn into a list of disks
disks = disks_data.strip().split()

warnings = []
criticals = []

for disk in disks:
    try:
        # List health and attributes
        smart_data = check_output(
            'smartctl -A -H {0}'.format(disk),
            shell=True,
        )

    except CalledProcessError as e:
        # If the disk doesn't support SMART, ignore it
        if 'Operation not supported by device' not in e.output:
            raise

        continue

    for line in smart_data.splitlines():
        # First check SMART's overall status
        if line.startswith('SMART overall-health self-assessment test result'):
            bits = line.split()
            test_result = bits[-1]

            if test_result != 'PASSED':
                criticals.append((
                    'Disk {0} has failed test, status: {1}'
                ).format(disk, test_result))
                continue

        # Ignore any non-attribute line
        if all(type_ not in line for type_ in ('Pre-fail', 'Old_age')):
            continue

        bits = line.split()
        name = bits[1]
        value = int(bits[3])
        threshold = int(bits[5])

        # From: https://superuser.com/a/354254
        # Each Attribute also has a Threshold value (whose range is 0 to 255)
        # which is printed under the heading "THRESH". If the Normalized value
        # is less than or equal to the Threshold value, then the Attribute is
        # said to have failed. If the Attribute is a pre-failure Attribute,
        # then disk failure is imminent.
        if value == threshold:
            warnings.append((
                'Attrbute {0} on disk {1} is at the threshold ({2})'
            ).format(name, disk, threshold))

        elif value < threshold:
            criticals.append((
                'Attribute {0} on disk {1} is below the threshold ({2}/{3})'
            ).format(name, disk, value, threshold))


exit_code = 0

if warnings:
    exit_code = 1
    print('\n'.join(warnings))

if criticals:
    exit_code = 2
    print('\n'.join(criticals))

if exit_code == 0:
    print('All disks healthy')


sys.exit(exit_code)
