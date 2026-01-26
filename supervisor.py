import subprocess
import time
import sys
import os

from dotenv import load_dotenv
load_dotenv()


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON = sys.executable

CONFIG = os.path.join(BASE_DIR, "collectors.yml")

CMD = [
    PYTHON,
    os.path.join(BASE_DIR, "main.py"),
    "--config",
    CONFIG,
]

print("[SUPERVISOR] Starting collector")
print("[SUPERVISOR] CMD:", " ".join(CMD))

while True:
    try:
        proc = subprocess.Popen(
            CMD,
            env=os.environ.copy(),  
        )
        print("[SUPERVISOR] Collector running (pid=%s)" % proc.pid)

        proc.wait()

        print("[SUPERVISOR] Collector exited, restarting in 5s...")
        time.sleep(5)

    except KeyboardInterrupt:
        print("[SUPERVISOR] Stopping supervisor")
        try:
            proc.terminate()
        except Exception:
            pass
        break

    except Exception as e:
        print("[SUPERVISOR] ERROR:", e)
        time.sleep(5)
