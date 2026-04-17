from pycomm3 import LogixDriver
from pycomm3.exceptions import CommError
import time
from typing import Any

from common.logger import get_logger

logger = get_logger("collector.rockwell")


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
        self._logical_by_plc_tag = {plc: logical for logical, plc in self.tag_map.items()}

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

        logger.info("Connected to Rockwell PLC ip=%s", self.ip)

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
            if not isinstance(results, list):
                results = [results]

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
                        "Debug read tag=%s value=%s type=%s",
                        logical_tag,
                        value,
                        type(value).__name__,
                    )

            self._consecutive_fails = 0
            return values

        except CommError as e:
            self._consecutive_fails += 1
            logger.error("Rockwell read failed ip=%s err=%s", self.ip, e)
            if self._consecutive_fails >= self.max_consecutive_fails:
                self._disconnect()
            return {}

        except Exception as e:
            self._consecutive_fails += 1
            logger.exception("Rockwell read crashed ip=%s err=%s", self.ip, e)
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
        return self._logical_by_plc_tag.get(plc_tag, plc_tag)
