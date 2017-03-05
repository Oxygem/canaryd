# canaryd
# File: canaryd/ctl/__main__.py
# Desc: entry point for canaryctl

from __future__ import print_function

from canaryd.exceptions import CanarydError
from canaryd.log import logger
from canaryd.remote import ApiError

from . import main


try:
    main()

except ApiError as e:
    logger.critical('API {0} error: {1}'.format(e.status_code, e.message))

except CanarydError:
    raise

except Exception:
    logger.critical('Unexpected exception:')
    raise
