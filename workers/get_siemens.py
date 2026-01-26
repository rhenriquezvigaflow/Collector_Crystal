from opcua import Client
from opcua.ua.uaerrors import UaError
import time


class SiemensSessionReader:
    def __init__(
        self,
        endpoint: str,
        tag_map: dict,
        timeout_sec: int = 4,
        username: str | None = None,
        password: str | None = None,
    ):
        self.endpoint = endpoint
        self.tag_map = tag_map
        self.timeout_sec = timeout_sec
        self.username = username
        self.password = password

        self.client: Client | None = None
        self.nodes: dict = {}
        self._connected = False

    # =========================
    # CONNECTION
    # =========================

    def connect(self):
        self.disconnect()

        client = Client(self.endpoint, timeout=self.timeout_sec)

        if self.username and self.password:
            client.set_user(self.username)
            client.set_password(self.password)

        client.connect()

        self.client = client
        self.nodes = {
            tag_id: client.get_node(node_id)
            for tag_id, node_id in self.tag_map.items()
        }

        self._connected = True

    def disconnect(self):
        if self.client:
            try:
                self.client.disconnect()
            except Exception:
                pass
        self.client = None
        self.nodes = {}
        self._connected = False

    # =========================
    # READ
    # =========================

    def read_once(self) -> dict:
        if not self._connected:
            self.connect()

        values = {}

        try:
            for tag_id, node in self.nodes.items():
                values[tag_id] = node.get_value()

            return values

        except UaError:
            #  reconectar en próximo ciclo
            self.disconnect()
            return {}

        except Exception:
            # cualquier otro error no rompe el loop 1s
            self.disconnect()
            return {}
