from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler

LOG_FILE_PATH = os.getenv("COLLECTOR_LOG_FILE_PATH", "logs/collector.log")
LOG_MAX_BYTES = int(os.getenv("COLLECTOR_LOG_MAX_BYTES", "10485760"))
LOG_BACKUP_COUNT = int(os.getenv("COLLECTOR_LOG_BACKUP_COUNT", "5"))
LOG_LEVEL = os.getenv("COLLECTOR_LOG_LEVEL", "INFO").strip().upper()


def get_logger(name: str = "collector"):
    os.makedirs("logs", exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    if not logger.handlers:
        file_handler = RotatingFileHandler(
            LOG_FILE_PATH,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)
        logger.propagate = False

    return logger
