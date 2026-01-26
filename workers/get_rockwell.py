from pycomm3 import LogixDriver
from pycomm3.exceptions import CommError
import time


class RockwellSessionReader:
    def __init__(
        self,
        ip: str,
        slot: int,
        tag_map: dict,
        force_reconnect_every_sec: int = 3600,
        max_consecutive_fails: int = 10,
        timeout_sec: float = 5.0,
    ):
        self.ip = ip
        self.slot = slot
        self.tag_map = tag_map
        self.force_reconnect_every_sec = force_reconnect_every_sec
        self.max_consecutive_fails = max_consecutive_fails
        self.timeout_sec = timeout_sec

        self._last_connect_ts: float = 0.0
        self._consecutive_fails: int = 0
        self._driver: LogixDriver | None = None

        # cache de direcciones PLC para batch read
        self._plc_tags = list(self.tag_map.values())

    # =========================
    # CONNECTION
    # =========================

    def _connect(self):
        self._disconnect()

        driver = LogixDriver(
            self.ip,
            slot=self.slot,
            timeout=self.timeout_sec,
        )
        driver.open()

        self._driver = driver
        self._last_connect_ts = time.time()
        self._consecutive_fails = 0

    def _disconnect(self):
        if self._driver:
            try:
                self._driver.close()
            except Exception:
                pass
        self._driver = None

    def _should_rotate(self) -> bool:
        return (
            self._driver is None
            or (time.time() - self._last_connect_ts) >= self.force_reconnect_every_sec
        )

    # =========================
    # READ (BATCH)
    # =========================

    def read_once(self) -> dict:
        if self._should_rotate():
            self._connect()

        values: dict = {}

        try:
            results = self._driver.read(*self._plc_tags)

            for res in results:
                if res is None:
                    continue

                # mapear PLC tag → logical tag_id
                logical_tag = self._find_logical_tag(res.tag)

                if res.error:
                    values[logical_tag] = None
                else:
                    values[logical_tag] = res.value

            self._consecutive_fails = 0
            return values

        except CommError:
            # error de comunicación (timeout, socket, etc.)
            self._consecutive_fails += 1
            if self._consecutive_fails >= self.max_consecutive_fails:
                self._disconnect()
            return {}

        except Exception:
            # error inesperado: no romper el loop
            self._consecutive_fails += 1
            if self._consecutive_fails >= self.max_consecutive_fails:
                self._disconnect()
            return {}

    # =========================
    # UTILS
    # =========================

    def _find_logical_tag(self, plc_tag: str) -> str:
        # inverso rápido del tag_map
        # (normalmente pocos tags, costo despreciable)
        for logical, plc in self.tag_map.items():
            if plc == plc_tag:
                return logical
        return plc_tag