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
