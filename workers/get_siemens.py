from typing import Any, Callable

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
        except UaError:
            self.disconnect()
            return {}
        except Exception:
            self.disconnect()
            return {}


SiemensReaderFactory = Callable[..., SiemensSessionReader]


class SiemensModulesReader:
    def __init__(
        self,
        modules: list[dict[str, Any]],
        *,
        supplemental_tags: dict[str, Any] | None = None,
        reader_factory: SiemensReaderFactory = SiemensSessionReader,
    ) -> None:
        self.supplemental_tags = dict(supplemental_tags or {})
        self._readers: list[tuple[SiemensSessionReader, tuple[str, ...]]] = []

        for module in modules:
            driver = str(module.get("driver") or "siemens").strip().lower()
            if driver not in {"siemens", "opcua"}:
                raise ValueError(f"Unsupported OPC UA module driver: {driver!r}")

            tag_map = module.get("tags") or {}
            if not isinstance(tag_map, dict) or not tag_map:
                continue

            endpoint = str(module.get("opc_server_url") or "").strip()
            if not endpoint:
                ip = str(module.get("ip") or "").strip()
                endpoint = f"opc.tcp://{ip}:4840" if ip else ""
            if not endpoint:
                raise ValueError("Siemens OPC UA module endpoint is required")

            reader = reader_factory(
                endpoint=endpoint,
                tag_map=tag_map,
                timeout_sec=float(module.get("timeout_sec", 4)),
                username=module.get("username"),
                password=module.get("password"),
            )
            self._readers.append((reader, tuple(tag_map)))

    def read_once(self) -> dict[str, Any]:
        values = dict(self.supplemental_tags)
        for reader, tag_ids in self._readers:
            try:
                module_values = reader.read_once()
            except Exception:
                module_values = {}

            if module_values:
                values.update(module_values)
            else:
                values.update({tag_id: None for tag_id in tag_ids})

        return values
