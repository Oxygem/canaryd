#!/usr/bin/env python

import sys

from subprocess import CalledProcessError

from canaryd.packages.check_output import check_output

SMART_RETURN_BITS = {
    0: False,  # command line parse error
    1: 'device open failed',
    2: 'SMART command failed',
    3: 'disk failing',
    # We track thresholds via stdout
    4: True,  # pre-fail attrs <= thresh
    5: True,  # pre-fail attrs <= thresh in past
    # We track errors via stdout
    6: True,  # error log
    7: True,  # self-test errors
}


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
            'smartctl -a {0}'.format(disk),
            shell=True,
        )

    except CalledProcessError as e:
        smart_data = e.output

        for i in SMART_RETURN_BITS:
            bit = e.returncode & i
            if bit and i in SMART_RETURN_BITS:
                return_bit = SMART_RETURN_BITS[i]

                if return_bit is False:
                    raise

                if return_bit is True:
                    continue

                criticals.append('Disk {0} error: {1}'.format(disk, return_bit))
                break

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

        # Skip where both the value and threshold are 0, like power_on_hours/etc
        if value == 0 and threshold == 0:
            continue

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
