"""
Logging configuration for XSOAR CLI.

Handles setup of the application file logger, including platform-aware log
path resolution and log rotation.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import NamedTuple


class LoggingSetup(NamedTuple):
    logger: logging.Logger
    handler: RotatingFileHandler


LOGGER_NAME = "xsoar_cli"
LOG_FILE_NAME = "xsoar-cli.log"
LOG_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
LOG_BACKUP_COUNT = 3


def get_log_path() -> Path:
    """Returns the platform-appropriate log file path under the user's home directory."""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Logs" / "xsoar-cli" / LOG_FILE_NAME
    if sys.platform == "win32":
        # Windows has not yet been properly tested with xsoar-cli. There may be unknown bugs here
        import os

        base = Path(os.environ["LOCALAPPDATA"]) if "LOCALAPPDATA" in os.environ else Path.home() / "AppData" / "Local"
        return base / "xsoar-cli" / "Logs" / LOG_FILE_NAME
    # Linux and other Unix-like systems follow the XDG Base Directory spec,
    # which designates ~/.local/state for application state data including logs.
    return Path.home() / ".local" / "state" / "xsoar-cli" / LOG_FILE_NAME


def setup_logging() -> LoggingSetup:
    """
    Configures the application file logger and returns a LoggingSetup containing
    both the logger and the file handler. Safe to call multiple times — additional
    handlers are not added if one is already configured. The handler is returned so
    the caller can adjust the log level after setup if needed.
    """
    logger = logging.getLogger(LOGGER_NAME)

    if logger.handlers:
        handler = logger.handlers[0]
        assert isinstance(handler, RotatingFileHandler)
        return LoggingSetup(logger=logger, handler=handler)

    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    log_path = get_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    handler = RotatingFileHandler(
        log_path,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setLevel(logging.INFO)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)-8s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    logger.addHandler(handler)
    return LoggingSetup(logger=logger, handler=handler)
