import subprocess
import time
import sys
import os

from dotenv import load_dotenv
from common.logger import get_logger
load_dotenv()


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON = sys.executable
logger = get_logger("collector.supervisor")

CONFIG = os.path.join(BASE_DIR, "collectors.yml")

CMD = [
    PYTHON,
    os.path.join(BASE_DIR, "main.py"),
    "--config",
    CONFIG,
]

logger.info("Starting collector supervisor")
logger.info("Command: %s", " ".join(CMD))

while True:
    try:
        proc = subprocess.Popen(
            CMD,
            env=os.environ.copy(),  
        )
        logger.info("Collector running pid=%s", proc.pid)

        proc.wait()

        logger.warning("Collector stopped, restarting in 5s")
        time.sleep(5)

    except KeyboardInterrupt:
        logger.info("Stopping collector supervisor")
        try:
            proc.terminate()
        except Exception:
            pass
        break

    except Exception as e:
        logger.error("Supervisor error: %s", e)
        time.sleep(5)
