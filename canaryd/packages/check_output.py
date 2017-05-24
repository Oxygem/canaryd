from subprocess import CalledProcessError, PIPE, Popen, STDOUT


def check_output(*popenargs, **kwargs):
    process = Popen(stdout=PIPE, stderr=STDOUT, *popenargs, **kwargs)
    output, _ = process.communicate()
    output = output.decode('utf-8')

    retcode = process.poll()
    if retcode:
        cmd = kwargs.get('args')
        if cmd is None:
            cmd = popenargs[0]

        # CalledProcessError doesn't have output in py 2.6 (CentOS 6), so we
        # can't pass it to the initialiser.
        exception = CalledProcessError(retcode, cmd)
        exception.output = output
        raise exception
    return output
