# canaryd
# File: canaryd/ctl/__main__.py
# Desc: entry point for canaryctl

from __future__ import print_function

from canaryd.log import logger
from canaryd.remote import ApiError

from . import main


try:
    main()

except ApiError as e:
    logger.critical('API {0} error: {1}({2})'.format(
        e.status_code,
        e.name,
        e.message,
    ))
