# v0.6.8

+ Make it possible to set settings comments to scripts (currently interval only)
+ Set the builtin `disk_health.py` script to have a 1hr interval
+ Add `check_paths` plugin setting for integrity plugin

# v0.6.7

+ Execute `rpm -qa` as nobody to avoid corrupting the rpm database

# v0.6.6

+ Fix `/lib64` and `/usr/lib64` integrity checks

# v0.6.5

+ Corrected release for `v0.6.4`

# v0.6.4

+ Expand integrity checks
+ Ignore `/etc/adjtime` for file integrity checks

# v0.6.3

+ Fix monitor plugin failing where interface speed cannot be read from `/sys`

# v0.6.2

+ Correct typo from `v0.6.1`!

# v0.6.1

+ Set a max size (1GB) for file integrity checks

# v0.6

+ Add **integrity** plugin to track important file owners/permissions/checksums
+ Add notion of "slow" plugins with a reduced collection interval
    * applied to packages, hardware and integrity plugins
+ Track/add `login_time` attribute to users plugin
+ Track/add `enabled` attribute to scripts plugin
+ Track network interface transmit/receive bytes in monitor plugin
+ Use `netstat` to find service ports if `lsof` isn't available
+ Python `3.7` testing/compatability
+ Rename `canaryctl scripts copy` -> `canaryctl scripts install`
+ Automatically enable compatible scripts on install/init
+ Gracefully exit the `canaryd` daemon when service stopped, stops offline issues/alerts
+ Modify how canaryd communicates with the Service Canary API


# v0.5.6

+ Fix bug with tracking invalid init.d scripts

# v0.5.5

+ Calculate disk space used by doing (max - available) rather than using `df` used
+ Optimise `lsof` (add `-b -l -L`)
+ Ignore more init scripts by default (networking, halt, etc)

# v0.5.4

+ Ignore `/etc/init.d/kcare`

# v0.5.3

+ Improve capture of `init.d` process PIDs
+ More fixes for parsing `lsof`!

# v0.5.2

+ Always set previous state, even if we failed
+ Skip invalid lsof lines
+ Fix cleaning up deleted items in hardware plugin

# v0.5.1

+ Ignore plugin exceptions on initial first run (potentially during system init)
+ Fix for error lines in lsof output (tracking service ports)

# v0.5

+ Extend the state daemon to handle/track plugin failures
    - Uses the latest `canary_server` updates
    - Handle plugins transitioning from broken -> working gracefully
+ Fix for systemd: ignore oneshot type services
+ Fix for service ports temporarily dissappearing
+ Fix when decoding command output in Python 2.6


# v0.4.5

+ Use `chardet` package to improve decoding of command output
+ Fix supervisor service PID not being an integer
+ Fix splitting of `lsof` to find listen ports for a PID

# v0.4.4

+ Add `X hr` support parsing uptime in the meta plugin
+ Sort user groups consistently
+ Fix timeout handling so we correctly cleanup any commands that timed out
+ Fix timed rotating log handling

# v0.4.3

+ Fix location of `cacert.pem` now packages are under `canaryd_packages/`

# v0.4.2

+ Fix issue generation for the `services` and `monitor` plugins
+ Fix Docker container inspection
+ Add `--all` option to `canaryctl state`
+ Add unit tests for plugins
+ Add `.travis.yml`/Travis tests

# 0.4.1

+ Fix monitor plugin CPU/IOWait collection

# v0.4

+ Refactor how plugins handle changes to support event grouping on the server side
    * Add methods:
        - `get_action_for_change`
        - `get_description_for_change`
        - `get_change_key`
        - `should_apply_change`
        - `generate_issues_from_change`
    * Removed/replacing:
        - `generate_events`
        - `is_change`
+ Use `netstat` over `lsof` to get PID -> port mappings (more reliable)
+ Improve/speed up `init.d` state collection
+ Better `init.d` script
+ Drop `set` as a valid plugin spec type (use list, like ES)


# v0.3.1

+ Fix bug in `which` checking

# v0.3

+ Add CLI events: `canaryctl event PLUGIN TYPE DESCRIPTION [DATA]`
+ Add **containers** plugin
+ Add **packages** plugin
+ Add `supervisord` support to services plugin
+ Track whether services are enabled, and which init system they belong too
+ Add `-h`, `-d` short options for `--help`, `--debug`
+ Start tracking/generating issues for IOWait
+ Start tracking min/max % for each interval in monitor plugin (enabling alerting on always/average/once)
+ Implement timeout for plugins so a hanging command doesn't break the daemon
+ Check/prepare plugins every iteration; use `find_executable` instead of just executing for performance
+ Add `log_rotation` and `log_rotation_count` settings
+ Fix: initd status
+ Fix: listing `*.pyc` files as scripts
+ Fix bug in hardware plugin where disks would change description (from `lshw`) incorrectly (now ignored)
+ Remove users from beta plugin (never a change)
+ Replace `check_output` recreation w/`subprocess32`


# v0.2.1

+ Fix monitor plugin edge case: ignore blank lines in `/proc/stat`

# v0.2

First release to include `.deb` and `.rpm` packages and build tools.

+ Add `monitor` plugin
+ Add custom scripts and `scripts` plugin
    * `canaryctl scripts`
    * `canaryctl scripts [enable|disable] disk_health.sh`
+ Add `services` plugin
    * monitors service port status
        - can generate warning/critical issues from this
    * this replaces other services plugins:
        - `initd`
        - `launchctl`
        - `upstart`
        - `systemd`
+ Rewrite `hardware` plugin to use `lshw`, not `dmidecode`, for better coverage
+ Rewrite `users` plugin to use Python's `grp` and `pwd` modules, for better (10x) performance


# v0.1.1

+ Don't overwrite extra config (api_base, etc) on register
+ Fix `launchctl` init
+ Fix state CLI command


# v0.1

+ Initial release
+ Plugins for:
    * `hardware`
    * `initd`
    * `iptables`
    * `launchctl`
    * `meta`
    * `sysctl`
    * `systemd`
    * `upstart`
    * `users`
