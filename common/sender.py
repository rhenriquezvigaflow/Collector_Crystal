import logging
import os
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

    def _build_body(self, payload) -> dict[str, Any]:
        body: dict[str, Any] = {
            "lagoon_id": str(payload.lagoon_id),
            "source": payload.source,
            "timestamp": payload.timestamp.isoformat(),
            "tags": payload.tags,
        }

        if self.send_events and payload.events:
            body["events"] = self._serialize_events(payload.events)

        return body

    def send(self, payload) -> bool:
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
            logger.error("backend unreachable: %s", exc)
            return False

    def close(self):
        self.session.close()
