# canaryd
# File: canaryd/ctl/__main__.py
# Desc: entry point for canaryctl

from __future__ import print_function

from canaryd.remote import ApiError

from . import main, scripts  # noqa


try:
    main()

except ApiError as e:
    e.log()

except Exception:
    # TODO: public Sentry logging

    raise
