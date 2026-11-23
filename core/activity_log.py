"""Local activity logging for the desktop automation prototype."""

import logging
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_DIRECTORY = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIRECTORY / "ztss_core.log"


def configure_activity_log():
    """Create a local log file and return the application logger."""
    LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("ztss_core")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        )
        logger.addHandler(handler)

    return logger
