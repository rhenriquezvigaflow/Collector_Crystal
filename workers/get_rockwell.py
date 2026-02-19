from pycomm3 import LogixDriver
from pycomm3.exceptions import CommError
import time
import logging
from typing import Any


logger = logging.getLogger("rockwell_reader")


class RockwellSessionReader:
    def __init__(
        self,
        ip: str,
        slot: int,
        tag_map: dict,
        force_reconnect_every_sec: int = 3600,
        max_consecutive_fails: int = 10,
        timeout_sec: float = 5.0,
        debug_types: bool = False,  
    ):
        self.ip = ip
        self.slot = slot
        self.tag_map = tag_map
        self.force_reconnect_every_sec = force_reconnect_every_sec
        self.max_consecutive_fails = max_consecutive_fails
        self.timeout_sec = timeout_sec
        self.debug_types = debug_types

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

        logger.info(f"Connected to Rockwell PLC {self.ip}")

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

    def read_once(self) -> dict[str, Any]:
        if self._should_rotate():
            self._connect()

        values: dict[str, Any] = {}

        try:
            results = self._driver.read(*self._plc_tags)

            for res in results:
                if res is None:
                    continue

                logical_tag = self._find_logical_tag(res.tag)

                if res.error:
                    values[logical_tag] = None
                    continue

                raw_value = res.value
                value = self._normalize_value(raw_value)

                values[logical_tag] = value
                if self.debug_types:
                    logger.warning(
                        f"PLC READ tag={logical_tag} "
                        f"value={value} type={type(value).__name__}"
                    )

            self._consecutive_fails = 0
            return values

        except CommError as e:
            self._consecutive_fails += 1
            logger.error(f"CommError reading PLC {self.ip}: {e}")
            if self._consecutive_fails >= self.max_consecutive_fails:
                self._disconnect()
            return {}

        except Exception as e:
            self._consecutive_fails += 1
            logger.exception(f"Unexpected error reading PLC {self.ip}: {e}")
            if self._consecutive_fails >= self.max_consecutive_fails:
                self._disconnect()
            return {}

    # =========================
    # UTILS
    # =========================

    def _normalize_value(self, value: Any) -> Any:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return int(value)
        if isinstance(value, float):
            return float(value)
        return value

    def _find_logical_tag(self, plc_tag: str) -> str:
        for logical, plc in self.tag_map.items():
            if plc == plc_tag:
                return logical
        return plc_tag
