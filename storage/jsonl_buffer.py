import os
import threading

_BUFFER_LOCK = threading.Lock()


def append(payload_json: str, path: str = "data/buffer.jsonl"):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    with _BUFFER_LOCK:
        with open(path, "a", encoding="utf-8") as f:
            f.write(payload_json)
            f.write("\n")
