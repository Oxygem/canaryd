# v0.2 (WIP)

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
