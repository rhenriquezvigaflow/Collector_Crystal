from __future__ import annotations

import logging
import os
import time
from datetime import datetime
from typing import Any

import requests
from requests.adapters import HTTPAdapter

logger = logging.getLogger("collector")


class BackendSender:
    def __init__(
        self,
        url: str,
        timeout: float = 3.0,
        send_events: bool = False,
        pool_connections: int = 50,
        pool_maxsize: int = 200,
    ):
        self.url = url
        self.timeout = timeout
        self.send_events = send_events
        self.api_key = os.getenv("COLLECTOR_API_KEY")
        self._error_log_interval_sec = float(
            os.getenv("COLLECTOR_SEND_ERROR_LOG_INTERVAL_SEC", "30")
        )
        self._last_error_signature: str | None = None
        self._last_error_log_monotonic = 0.0

        if not self.api_key:
            logger.error("COLLECTOR_API_KEY NOT SET")

        self.session = requests.Session()
        adapter = HTTPAdapter(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=0,
            pool_block=False,
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        self._headers = {"X-Api-Key": self.api_key or ""}

    def _serialize_events(self, events: list[Any]) -> list[Any]:
        serialized: list[Any] = []
        for event in events:
            if hasattr(event, "model_dump"):
                serialized.append(event.model_dump(mode="json"))
            else:
                serialized.append(event)
        return serialized

    def _serialize_timestamp(self, value: Any) -> str | None:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return None

    def _build_body(self, payload: Any) -> dict[str, Any]:
        if isinstance(payload, dict):
            body: dict[str, Any] = {
                "lagoon_id": str(payload.get("lagoon_id", "")),
                "source": payload.get("source"),
                "timestamp": self._serialize_timestamp(payload.get("timestamp")),
                "tags": payload.get("tags") or {},
            }
            if self.send_events and payload.get("events"):
                body["events"] = self._serialize_events(payload["events"])
            return body

        body = {
            "lagoon_id": str(payload.lagoon_id),
            "source": payload.source,
            "timestamp": payload.timestamp.isoformat(),
            "tags": payload.tags,
        }

        if self.send_events and payload.events:
            body["events"] = self._serialize_events(payload.events)

        return body

    def _log_send_error(self, exc: Exception) -> None:
        signature = f"{type(exc).__name__}:{exc}"
        now_monotonic = time.monotonic()
        should_log = (
            signature != self._last_error_signature
            or now_monotonic - self._last_error_log_monotonic
            >= self._error_log_interval_sec
        )
        if not should_log:
            return

        self._last_error_signature = signature
        self._last_error_log_monotonic = now_monotonic
        logger.error("backend unreachable url=%s err=%s", self.url, exc)

    def send(self, payload: Any) -> bool:
        if not self.api_key:
            return False

        try:
            response = self.session.post(
                self.url,
                json=self._build_body(payload),
                headers=self._headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return True
        except Exception as exc:
            self._log_send_error(exc)
            return False

    def close(self):
        self.session.close()
