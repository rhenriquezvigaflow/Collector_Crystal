import time
from pycomm3 import LogixDriver

class RockwellSessionReader:
    def __init__(
        self,
        ip: str,
        slot: int,
        tag_map: dict,
        force_reconnect_every_sec: int = 3600,
        max_consecutive_fails: int = 10,
    ):
        self.ip = ip
        self.slot = slot
        self.tag_map = tag_map
        self.force_reconnect_every_sec = force_reconnect_every_sec
        self.max_consecutive_fails = max_consecutive_fails

        self._path = f"{ip}/{slot}"
        self._plc = None
        self._session_start = 0.0
        self._consecutive_fails = 0

    def connect(self):
        # Mantener el driver vivo
        self._plc = LogixDriver(self._path)
        self._plc.open()
        self._session_start = time.time()
        self._consecutive_fails = 0

    def close(self):
        try:
            if self._plc:
                self._plc.close()
        finally:
            self._plc = None

    def should_rotate(self) -> bool:
        return (time.time() - self._session_start) >= self.force_reconnect_every_sec

    def read_once(self) -> dict:
        """
        Lee TODOS los tags en una sola llamada (batch) y devuelve:
        {"d0": value, "d1": value, ...}
        """
        if self._plc is None:
            raise RuntimeError("PLC session not open")

        plc_tags = list(self.tag_map.values())
        logical_keys = list(self.tag_map.keys())

        # batch read
        results = self._plc.read(*plc_tags)

        out = {}
        any_bad = False

        for logical, res in zip(logical_keys, results):
            if res is None or getattr(res, "error", None):
                out[logical] = None
                any_bad = True
            else:
                out[logical] = res.value

        if any_bad:
            self._consecutive_fails += 1
        else:
            self._consecutive_fails = 0

        if self._consecutive_fails >= self.max_consecutive_fails:
            raise Exception(f"Too many consecutive fails ({self._consecutive_fails})")

        return out
