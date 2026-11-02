"""Logging setup.

A single format for the whole application. Nothing is filtered on the
way out, so whatever a handler passes to logger.info reaches the log
aggregator as written.
"""

import logging
import sys

FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configure(level: int = logging.INFO) -> logging.Logger:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(FORMAT))

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]
    return logging.getLogger("bharatbazaar")
