import time
import yaml
import argparse
import os
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict

from dotenv import load_dotenv

from common.payload import NormalizedPayload
from common.time import utc_now
from common.sender import BackendSender

from workers.get_rockwell import RockwellSessionReader
from workers.get_siemens import SiemensSessionReader

# =========================
# ENV
# =========================
load_dotenv()

# ==================================================
# SILENCIAR LOGS DE LIBRERÍAS (OPC / ROCKWELL)
# ==================================================

logging.getLogger("opcua").setLevel(logging.WARNING)
logging.getLogger("opcua.client").setLevel(logging.WARNING)
logging.getLogger("opcua.server").setLevel(logging.WARNING)
logging.getLogger("opcua.uaprotocol").setLevel(logging.WARNING)

logging.getLogger("pycomm3").setLevel(logging.WARNING)
logging.getLogger("pycomm3.cip_driver").setLevel(logging.WARNING)
logging.getLogger("pycomm3.logix_driver").setLevel(logging.WARNING)

logging.getLogger("urllib3").setLevel(logging.WARNING)


# =========================
# Event Detector
# =========================

class EventDetector:
    """
    Detecta cambios de estado (FALSE→TRUE / TRUE→FALSE)
    Mantiene estado en memoria por (lagoon_id, tag_id)
    """

    def __init__(self):
        self.last_states: Dict[tuple, bool] = {}

    def process(
        self,
        lagoon_id: str,
        tags: dict,
        ts,
        event_tags: dict,
    ) -> list[dict]:
        """
        event_tags:
        {
            "pump_running": "Pump Running",
            "blower_status": "Blower Status"
        }
        """
        events = []

        for tag_id, label in event_tags.items():
            if tag_id not in tags:
                continue

            value = bool(tags[tag_id])
            key = (lagoon_id, tag_id)
            prev = self.last_states.get(key)

            # Primera lectura → solo memorizar
            if prev is None:
                self.last_states[key] = value
                continue

            # FALSE → TRUE → abrir evento
            if prev is False and value is True:
                events.append({
                    "type": "OPEN",
                    "lagoon_id": lagoon_id,
                    "tag_id": tag_id,
                    "tag_label": label,
                    "ts": ts.isoformat(),
                })

            # TRUE → FALSE → cerrar evento
            elif prev is True and value is False:
                events.append({
                    "type": "CLOSE",
                    "lagoon_id": lagoon_id,
                    "tag_id": tag_id,
                    "ts": ts.isoformat(),
                })

            self.last_states[key] = value

        return events


# =========================
# Config helpers
# =========================

def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_path(base_file: str, maybe_relative: str) -> str:
    if os.path.isabs(maybe_relative):
        return maybe_relative
    base_dir = os.path.dirname(os.path.abspath(base_file))
    return os.path.join(base_dir, maybe_relative)


def load_plc_configs(config_path: str) -> tuple[list[dict], dict]:
    root = load_config(config_path)

    if "plcs" not in root:
        return [root], root

    plc_configs: list[dict] = []
    for entry in root["plcs"]:
        if "include" in entry:
            included_path = resolve_path(config_path, entry["include"])
            plc_configs.append(load_config(included_path))
        else:
            plc_configs.append(entry)

    return plc_configs, root


def get_backend_sender(cfg: dict, root_cfg: dict) -> BackendSender | None:
    backend_url = (cfg.get("backend") or {}).get("url")
    if not backend_url:
        backend_url = (root_cfg.get("backend") or {}).get("url")
    if backend_url:
        return BackendSender(backend_url)
    return None


# =========================
# Main PLC loop
# =========================

def run_one_plc(cfg: dict, root_cfg: dict):
    lagoon_id = cfg["lagoon_id"]
    source = cfg["source"]
    poll = float(cfg.get("poll_seconds", 1))

    sender = get_backend_sender(cfg, root_cfg)
    event_detector = EventDetector()
    event_tags = cfg.get("event_tags", {})  # SOLO tags booleanos

    if source == "rockwell":
        reader = RockwellSessionReader(
            ip=cfg["rockwell"]["ip"],
            slot=int(cfg["rockwell"].get("slot", 0)),
            tag_map=cfg["tags"],
            force_reconnect_every_sec=int(cfg.get("force_reconnect_every_sec", 3600)),
            max_consecutive_fails=int(cfg.get("max_consecutive_fails", 10)),
        )
    elif source == "siemens":
        si = cfg["siemens"]
        reader = SiemensSessionReader(
            endpoint=si["opc_server_url"],
            tag_map=cfg["tags"],
            username=si.get("username"),
            password=si.get("password"),
        )
    else:
        raise ValueError(f"Unsupported source: {source}")

    print(f"START {source} lagoon={lagoon_id}")

    while True:
        cycle_start = time.perf_counter()

        try:
            raw_tags = reader.read_once()
        except Exception as e:
            elapsed = time.perf_counter() - cycle_start
            print(f"ERR {source} lagoon={lagoon_id} err={e} cycle={elapsed*1000:.1f}ms")
            time.sleep(min(1.0, poll))
            continue

        payload = NormalizedPayload(
            lagoon_id=lagoon_id,
            source=source,
            timestamp=utc_now(),
            tags=raw_tags,
        )

        # =========================
        # EVENT DETECTION
        # =========================
        events = event_detector.process(
            lagoon_id=lagoon_id,
            tags=raw_tags,
            ts=payload.timestamp,
            event_tags=event_tags,
        )

        if events:
            payload.events = events

        # =========================
        # SEND TO BACKEND
        # =========================
        if sender:
            sender.send(payload)

        elapsed = time.perf_counter() - cycle_start
        print(
            f"OK {source} lagoon={lagoon_id} ts={payload.timestamp.isoformat()} "
            f"tags={len(raw_tags)} events={len(events)} "
            f"cycle={elapsed*1000:.1f}ms"
        )

        sleep_for = poll - elapsed
        if sleep_for > 0:
            time.sleep(sleep_for)


# =========================
# Entrypoint
# =========================

def main(config_path: str):
    plc_configs, root_cfg = load_plc_configs(config_path)

    if len(plc_configs) == 1:
        run_one_plc(plc_configs[0], root_cfg)
        return

    print(f"MASTER: starting {len(plc_configs)} PLCs")
    with ThreadPoolExecutor(max_workers=len(plc_configs)) as ex:
        for cfg in plc_configs:
            ex.submit(run_one_plc, cfg, root_cfg)

        while True:
            time.sleep(60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    main(args.config)
