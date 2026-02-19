import os
import requests
import logging

logger = logging.getLogger("collector")
logging.basicConfig(level=logging.INFO)


class BackendSender:
    def __init__(self, url: str, timeout: float = 3.0):
        self.url = url
        self.timeout = timeout

        self.api_key = os.getenv("COLLECTOR_API_KEY")

        logger.info(f"Collector API KEY = {self.api_key}")

        if not self.api_key:
            logger.error("COLLECTOR_API_KEY NOT SET")

    def send(self, payload):
        try:
            r = requests.post(
                self.url,
                json={
                    "lagoon_id": str(payload.lagoon_id),
                    "source": payload.source,
                    "timestamp": payload.timestamp.isoformat(),  # UTC
                    "tags": payload.tags,
                },
                headers={
                    "X-Api-Key": self.api_key,
                },
                timeout=self.timeout,
            )

            r.raise_for_status()
            return True

        except Exception as e:
            logger.error(f"backend unreachable: {e}")
            return False
