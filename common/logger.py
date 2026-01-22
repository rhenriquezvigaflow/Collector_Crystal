import logging
import os

def get_logger():
    os.makedirs("logs", exist_ok=True)

    logger = logging.getLogger("collector")
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    if not logger.handlers:
        fh = logging.FileHandler("logs/collector.log", encoding="utf-8")
        fh.setFormatter(formatter)

        sh = logging.StreamHandler()
        sh.setFormatter(formatter)

        logger.addHandler(fh)
        logger.addHandler(sh)

    return logger
