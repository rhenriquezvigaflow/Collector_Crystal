import os

def append(payload_json: str):
    os.makedirs("data", exist_ok=True)
    with open("data/buffer.jsonl", "a", encoding="utf-8") as f:
        f.write(payload_json + "\n")
