from subprocess import CalledProcessError, PIPE, Popen


def check_output(*popenargs, **kwargs):
    process = Popen(stdout=PIPE, *popenargs, **kwargs)
    output, _ = process.communicate()
    retcode = process.poll()
    if retcode:
        cmd = kwargs.get('args')
        if cmd is None:
            cmd = popenargs[0]
        raise CalledProcessError(retcode, cmd)
    return output
