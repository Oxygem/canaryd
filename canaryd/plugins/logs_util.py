from threading import Thread

from canaryd_packages.six.moves.queue import Queue

from canaryd.subprocess import ensure_command_tuple, PIPE, Popen, STDOUT


def _enqueue_process_output(process, queue):
    while True:
        line = process.stdout.readline()
        queue.put(line)
        if not line:
            break


def follow_command_output(command):
    output_queue = Queue()

    command = ensure_command_tuple(command)

    process = Popen(
        command,
        stdout=PIPE,
        stderr=STDOUT,
    )

    thread = Thread(
        target=_enqueue_process_output,
        args=(process, output_queue),
    )
    thread.daemon = True  # auto-cleanup on main process exit
    thread.start()

    return output_queue


def tail_and_follow_file(filename):
    return follow_command_output(('tail', '-F', filename))


def parse_auth_logs(line):
    return line


def parse_dmesg_logs(line):
    return line


def parse_system_logs(line):
    return line


def parse_lynis_logs(line):
    return line
