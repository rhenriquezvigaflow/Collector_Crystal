import time
import yaml
import argparse
import os
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from common.payload import NormalizedPayload
from common.time import utc_now
from common.sender import BackendSender

from workers.get_rockwell import RockwellSessionReader
from workers.get_siemens import SiemensSessionReader

# SOLO ESTO ES NUEVO
from normalizer.tot_delta_normalizer import TotDeltaNormalizer


# =========================
# ENV
# =========================
load_dotenv()

logging.getLogger("opcua").setLevel(logging.WARNING)
logging.getLogger("pycomm3").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


# ==========================================================
# BOOLEAN EVENT DETECTOR
# ==========================================================

class BooleanEventDetector:

    def __init__(self):
        self.last_states: Dict[tuple, bool] = {}

    def process(
        self,
        lagoon_id: str,
        tags: Dict[str, Any],
        ts,
        event_tags: Dict[str, str],
    ) -> list[dict]:

        events = []

        for tag_id, label in event_tags.items():
            if tag_id not in tags:
                continue

            raw_value = tags[tag_id]
            if raw_value is None:
                continue

            value = bool(raw_value)
            key = (lagoon_id, tag_id)
            prev = self.last_states.get(key)

            if prev is None:
                self.last_states[key] = value
                continue

            if prev is False and value is True:
                events.append({
                    "type": "OPEN",
                    "lagoon_id": lagoon_id,
                    "tag_id": tag_id,
                    "tag_label": label,
                    "alert_type": "BOOLEAN",
                    "state": int(value),
                    "ts": ts.isoformat(),
                })

            elif prev is True and value is False:
                events.append({
                    "type": "CLOSE",
                    "lagoon_id": lagoon_id,
                    "tag_id": tag_id,
                    "alert_type": "BOOLEAN",
                    "state": int(value),
                    "ts": ts.isoformat(),
                })

            self.last_states[key] = value

        return events


# ==========================================================
# STATE EVENT DETECTOR
# ==========================================================

class StateEventDetector:

    def __init__(self):
        self.last_states: Dict[tuple, int] = {}

    def process(
        self,
        lagoon_id: str,
        tags: Dict[str, Any],
        ts,
    ) -> list[dict]:

        events = []

        for tag_id, raw_value in tags.items():

            if not isinstance(raw_value, int):
                continue

            if raw_value not in (0, 1, 2, 3):
                continue

            key = (lagoon_id, tag_id)
            prev = self.last_states.get(key)

            if prev is None:
                self.last_states[key] = raw_value
                continue

            if prev != raw_value:
                events.append({
                    "type": "STATE_CHANGE",
                    "lagoon_id": lagoon_id,
                    "tag_id": tag_id,
                    "alert_type": "STATE",
                    "previous_state": prev,
                    "state": raw_value,
                    "ts": ts.isoformat(),
                })

            self.last_states[key] = raw_value

        return events


# =========================
# CONFIG
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


# ==========================================================
# MAIN LOOP
# ==========================================================

def run_one_plc(cfg: dict, root_cfg: dict):

    lagoon_id = cfg["lagoon_id"]
    source = cfg["source"]
    poll = float(cfg.get("poll_seconds", 1))

    lagoon_timezone = cfg.get("timezone")
    if not lagoon_timezone:
        raise ValueError(f"Timezone not specified in config for lagoon {lagoon_id}")

    tz = ZoneInfo(lagoon_timezone)

    sender = get_backend_sender(cfg, root_cfg)

    boolean_detector = BooleanEventDetector()
    state_detector = StateEventDetector()

    # SOLO ESTO ES NUEVO
    tot_normalizer = TotDeltaNormalizer()

    event_tags = cfg.get("event_tags", {})

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

        # =========================
        # COPIA DEFENSIVA
        # =========================
        tags = dict(raw_tags)

        # =========================
        # WM001 TOT -> DELTA
        # =========================
        TOT_TAG = "WM01_TOT_SCADA"
        DELTA_TAG = "WM01_TOT_DELTA_SCADA"

        if TOT_TAG in tags:
            key = f"{lagoon_id}:{TOT_TAG}"
            delta = tot_normalizer.compute(key, tags.get(TOT_TAG))
            tags[DELTA_TAG] = delta


        timestamp_utc = utc_now()


        payload = NormalizedPayload(
            lagoon_id=lagoon_id,
            source=source,
            timestamp=timestamp_utc,
            tags=tags,
        )


        # BOOLEAN EVENTS
        bool_events = boolean_detector.process(
            lagoon_id=lagoon_id,
            tags=tags,
            ts=payload.timestamp,
            event_tags=event_tags,
        )

        # STATE EVENTS
        state_events = state_detector.process(
            lagoon_id=lagoon_id,
            tags=tags,
            ts=payload.timestamp,
        )

        all_events = bool_events + state_events

        if all_events:
            payload.events = all_events

        if sender:
            sender.send(payload)
            elapsed = time.perf_counter() - cycle_start

            print(
                f"OK {source} lagoon={lagoon_id} "
                f"utc={timestamp_utc.isoformat()} "
                f"tags={len(tags)} "
                f"events={len(all_events)} "
                f"cycle={elapsed*1000:.1f}ms"
            )

        elapsed = time.perf_counter() - cycle_start
        sleep_for = poll - elapsed
        if sleep_for > 0:
            time.sleep(sleep_for)


# =========================
# ENTRYPOINT
# =========================

def main(config_path: str):
    plc_configs, root_cfg = load_plc_configs(config_path)

    if len(plc_configs) == 1:
        run_one_plc(plc_configs[0], root_cfg)
        return

    print(f"MASTER: starting {len(plc_configs)} PLCs")

    with ThreadPoolExecutor(max_workers=len(plc_configs)) as ex:
        futures = []
        for cfg in plc_configs:
            futures.append(ex.submit(run_one_plc, cfg, root_cfg))

        for f in futures:
            try:
                f.result()
            except Exception as e:
                print("[THREAD ERROR]", e)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    main(args.config)
