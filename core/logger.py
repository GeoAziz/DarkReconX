"""core.logger

Logging helpers for DarkReconX. Exposes `get_logger(name, logfile=None)`
which returns a configured `logging.Logger`. If `rich` is available the
RichHandler is used to get colored, nicer output.
"""

import logging
from typing import Optional

try:
    from rich.logging import RichHandler
    _RICH = True
except Exception:
    RichHandler = logging.StreamHandler
    _RICH = False


def get_logger(name: str, logfile: Optional[str] = None, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level)
    if _RICH:
        handler = RichHandler(rich_tracebacks=True)
    else:
        handler = logging.StreamHandler()

    fmt = "[%(asctime)s] %(levelname)s - %(name)s: %(message)s"
    handler.setFormatter(logging.Formatter(fmt))
    logger.addHandler(handler)

    if logfile:
        fh = logging.FileHandler(logfile)
        fh.setFormatter(logging.Formatter(fmt))
        logger.addHandler(fh)

    return logger


# Backwards compatible simple logger wrapper
class Logger:
    def __init__(self, name: str = "DarkReconX"):
        self._log = get_logger(name)

    def info(self, msg: str):
        self._log.info(msg)

    def warn(self, msg: str):
        self._log.warning(msg)

    def error(self, msg: str):
        self._log.error(msg)
