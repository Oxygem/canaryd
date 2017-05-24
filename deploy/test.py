from pyinfra.modules import server

SUDO = True


server.shell(
    '/opt/canaryd/test.py',
)
