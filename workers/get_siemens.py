from typing import Any

from common.logger import get_logger
from opcua import Client
from opcua.ua.uaerrors import UaError

logger = get_logger("collector.siemens")


class SiemensSessionReader:
    def __init__(
        self,
        endpoint: str,
        tag_map: dict,
        timeout_sec: float = 4,
        username: str | None = None,
        password: str | None = None,
    ):
        self.endpoint = endpoint
        self.tag_map = tag_map
        self.timeout_sec = timeout_sec
        self.username = username
        self.password = password

        self.client: Client | None = None
        self.nodes: dict[str, Any] = {}
        self._tag_ids: list[str] = []
        self._nodes_in_order: list[Any] = []
        self._connected = False

    def connect(self):
        self.disconnect()

        client = Client(self.endpoint, timeout=self.timeout_sec)

        if self.username and self.password:
            client.set_user(self.username)
            client.set_password(self.password)

        client.connect()

        self.client = client
        self.nodes = {tag_id: client.get_node(node_id) for tag_id, node_id in self.tag_map.items()}
        self._tag_ids = list(self.nodes.keys())
        self._nodes_in_order = [self.nodes[tag_id] for tag_id in self._tag_ids]
        self._connected = True

    def disconnect(self):
        if self.client:
            try:
                self.client.disconnect()
            except Exception:
                pass

        self.client = None
        self.nodes = {}
        self._tag_ids = []
        self._nodes_in_order = []
        self._connected = False

    def read_once(self) -> dict:
        if not self._connected:
            self.connect()

        if not self.client:
            return {}

        try:
            raw_values = self.client.get_values(self._nodes_in_order)
            return {tag_id: value for tag_id, value in zip(self._tag_ids, raw_values)}
        except UaError as exc:
            logger.warning("Siemens read failed endpoint=%s err=%s", self.endpoint, exc)
            self.disconnect()
            return {}
        except Exception as exc:
            logger.error("Siemens read crashed endpoint=%s err=%s", self.endpoint, exc)
            self.disconnect()
            return {}
