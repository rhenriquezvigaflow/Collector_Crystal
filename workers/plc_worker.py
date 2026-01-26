# workers/plc_worker.py
import time
import threading
from common.payload import NormalizedPayload
from common.time import utc_now

class PLCWorker(threading.Thread):
    def __init__(self, name, reader, lagoon_id, source, poll_seconds, out_queue):
        super().__init__(daemon=True)
        self.name = name
        self.reader = reader
        self.lagoon_id = lagoon_id
        self.source = source
        self.poll_seconds = poll_seconds
        self.out_queue = out_queue
        self.running = True

    def run(self):
        next_tick = time.perf_counter()

        while self.running:
            cycle_start = time.perf_counter()

            try:
                tags = self.reader.read_once()
                payload = NormalizedPayload(
                    lagoon_id=self.lagoon_id,
                    source=self.source,
                    timestamp=utc_now(),
                    tags=tags,
                )
                self.out_queue.put(payload)
            except Exception as e:
                print(f"[{self.name}] PLC error: {e}")

            next_tick += self.poll_seconds
            sleep_for = next_tick - time.perf_counter()
            if sleep_for > 0:
                time.sleep(sleep_for)
