#!/bin/sh

### BEGIN INIT INFO
# Provides:          canaryd
# Required-Start:    $remote_fs $syslog
# Required-Stop:     $remote_fs $syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Put a short description of the service here
# Description:       Put a long description of the service here
### END INIT INFO

DAEMON=CANARYD_LOCATION
DAEMON_NAME=canaryd
DAEMON_USER=root
PIDFILE=/var/run/$DAEMON_NAME.pid
DAEMON_OPTS=""

# Load any defaults
if [ -f "/etc/default/$DAEMON_NAME" ]; then
    . /etc/default/$DAEMON_NAME
fi

. /lib/lsb/init-functions


# Handlers

do_start () {
    log_daemon_msg "Starting $DAEMON_NAME..."

    start-stop-daemon \
        --start --background --pidfile $PIDFILE --make-pidfile  \
        --user $DAEMON_USER --chuid $DAEMON_USER --startas $DAEMON \
        -- $DAEMON_OPTS

    log_end_msg $?
}

do_stop () {
    log_daemon_msg "Stopping $DAEMON_NAME..."

    start-stop-daemon \
        --stop --pidfile $PIDFILE --retry 10

    log_end_msg $?
}


# Run it!

case "$1" in

    start|stop)
        do_${1}
        ;;

    restart|reload|force-reload)
        do_stop
        do_start
        ;;

    status)
        status_of_proc "$DAEMON_NAME" "$DAEMON" && exit 0 || exit $?
        ;;

    *)
        echo "Usage: /etc/init.d/$DAEMON_NAME {start|stop|restart|status}"
        exit 1
        ;;

esac
exit 0
