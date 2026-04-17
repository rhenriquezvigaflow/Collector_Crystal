import argparse
import logging
import os
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from queue import Empty, Full, Queue
from typing import Any, Dict
from zoneinfo import ZoneInfo

import yaml
from dotenv import load_dotenv

from common.logger import get_logger
from common.payload import NormalizedPayload
from common.sender import BackendSender
from common.time import utc_now
from normalizer.tot_delta_normalizer import TotDeltaNormalizer
from storage import jsonl_buffer
from workers.get_rockwell import RockwellSessionReader
from workers.get_siemens import SiemensSessionReader

load_dotenv()

logging.getLogger("opcua").setLevel(logging.WARNING)
logging.getLogger("pycomm3").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

logger = get_logger()

TOT_TAG = "WM01_TOT_SCADA"
DELTA_TAG = "WM01_TOT_DELTA_SCADA"


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
        events: list[dict] = []

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
                events.append(
                    {
                        "type": "OPEN",
                        "lagoon_id": lagoon_id,
                        "tag_id": tag_id,
                        "tag_label": label,
                        "alert_type": "BOOLEAN",
                        "state": int(value),
                        "ts": ts.isoformat(),
                    }
                )
            elif prev is True and value is False:
                events.append(
                    {
                        "type": "CLOSE",
                        "lagoon_id": lagoon_id,
                        "tag_id": tag_id,
                        "alert_type": "BOOLEAN",
                        "state": int(value),
                        "ts": ts.isoformat(),
                    }
                )

            self.last_states[key] = value

        return events


class StateEventDetector:
    def __init__(self):
        self.last_states: Dict[tuple, int] = {}

    def process(self, lagoon_id: str, tags: Dict[str, Any], ts) -> list[dict]:
        events: list[dict] = []

        for tag_id, raw_value in tags.items():
            if isinstance(raw_value, bool):
                continue
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
                events.append(
                    {
                        "type": "STATE_CHANGE",
                        "lagoon_id": lagoon_id,
                        "tag_id": tag_id,
                        "alert_type": "STATE",
                        "previous_state": prev,
                        "state": raw_value,
                        "ts": ts.isoformat(),
                    }
                )

            self.last_states[key] = raw_value

        return events


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


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


def as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "y", "on"}:
            return True
        if lowered in {"0", "false", "no", "n", "off"}:
            return False
    return default


def get_runtime_option(cfg: dict, root_cfg: dict, key: str, default: Any) -> Any:
    cfg_runtime = cfg.get("runtime") or {}
    root_runtime = root_cfg.get("runtime") or {}

    if key in cfg_runtime:
        return cfg_runtime[key]
    if key in cfg:
        return cfg[key]
    if key in root_runtime:
        return root_runtime[key]
    if key in root_cfg:
        return root_cfg[key]
    return default


def get_backend_sender(cfg: dict, root_cfg: dict) -> BackendSender | None:
    backend_cfg = dict(root_cfg.get("backend") or {})
    backend_cfg.update(cfg.get("backend") or {})

    backend_url = backend_cfg.get("url")
    if not backend_url:
        return None

    return BackendSender(
        url=backend_url,
        timeout=float(backend_cfg.get("timeout_sec", 3.0)),
        send_events=as_bool(backend_cfg.get("send_events", False), False),
        pool_connections=int(backend_cfg.get("pool_connections", 50)),
        pool_maxsize=int(backend_cfg.get("pool_maxsize", 200)),
    )


def spool_payload(payload: NormalizedPayload):
    try:
        jsonl_buffer.append_for_lagoon(
            lagoon_id=str(payload.lagoon_id),
            payload_json=payload.model_dump_json(),
        )
    except Exception as exc:
        logger.error(
            "[BUFFER ERROR] lagoon=%s err=%s",
            payload.lagoon_id,
            exc,
        )


def send_with_retry(
    sender: BackendSender,
    payload: NormalizedPayload,
    retry_attempts: int,
    retry_backoff_base_sec: float,
    retry_backoff_max_sec: float,
) -> bool:
    attempts = max(0, retry_attempts)
    max_attempts = attempts + 1

    for attempt in range(1, max_attempts + 1):
        if sender.send(payload):
            return True

        if attempt >= max_attempts:
            break

        delay_sec = min(
            retry_backoff_base_sec * (2 ** (attempt - 1)),
            retry_backoff_max_sec,
        )
        time.sleep(max(0.0, delay_sec))

    return False


def replay_spool(
    lagoon_id: str,
    sender: BackendSender,
    replay_batch_size: int,
) -> tuple[int, int, int]:
    return jsonl_buffer.replay_for_lagoon(
        lagoon_id=lagoon_id,
        send_payload=sender.send,
        max_items=max(1, replay_batch_size),
    )


def enqueue_payload(send_queue: Queue, payload: NormalizedPayload, policy: str) -> bool:
    if policy == "block":
        send_queue.put(payload)
        return True

    try:
        send_queue.put_nowait(payload)
        return True
    except Full:
        if policy != "drop_oldest":
            return False

    try:
        _ = send_queue.get_nowait()
        send_queue.task_done()
    except Empty:
        return False

    try:
        send_queue.put_nowait(payload)
        return True
    except Full:
        return False


def sender_worker_loop(
    lagoon_id: str,
    sender: BackendSender,
    send_queue: Queue,
    spool_on_fail: bool,
    log_every_n_sends: int,
    replay_batch_size: int,
    retry_attempts: int,
    retry_backoff_base_sec: float,
    retry_backoff_max_sec: float,
):
    sent = 0
    failed = 0

    while True:
        if send_queue.qsize() == 0:
            replayed, pending_spool, dropped_spool = replay_spool(
                lagoon_id=lagoon_id,
                sender=sender,
                replay_batch_size=replay_batch_size,
            )
            if replayed or dropped_spool:
                logger.info(
                    "[SPOOL REPLAY] lagoon=%s replayed=%s pending=%s dropped=%s",
                    lagoon_id,
                    replayed,
                    pending_spool,
                    dropped_spool,
                )

        try:
            payload = send_queue.get(timeout=1.0)
        except Empty:
            continue

        try:
            ok = send_with_retry(
                sender=sender,
                payload=payload,
                retry_attempts=retry_attempts,
                retry_backoff_base_sec=retry_backoff_base_sec,
                retry_backoff_max_sec=retry_backoff_max_sec,
            )
            if ok:
                sent += 1
            else:
                failed += 1
                if spool_on_fail:
                    spool_payload(payload)
        except Exception as exc:
            failed += 1
            logger.error(
                "[SENDER ERROR] lagoon=%s err=%s",
                lagoon_id,
                exc,
            )
            if spool_on_fail:
                spool_payload(payload)
        finally:
            send_queue.task_done()

        total = sent + failed
        if log_every_n_sends > 0 and total > 0 and total % log_every_n_sends == 0:
            logger.debug(
                "[COLLECTOR SEND STATS] lagoon=%s sent=%s failed=%s queue=%s",
                lagoon_id,
                sent,
                failed,
                send_queue.qsize(),
            )


def run_one_plc(cfg: dict, root_cfg: dict):
    lagoon_id = cfg["lagoon_id"]
    source = str(cfg["source"]).strip().lower()
    poll = float(cfg.get("poll_seconds", 1))
    if poll <= 0:
        logger.warning("[COLLECTOR CONFIG] lagoon=%s reason=invalid_poll_seconds fallback=0.1", lagoon_id)
        poll = 0.1

    lagoon_timezone = cfg.get("timezone")
    if not lagoon_timezone:
        raise ValueError(f"Timezone not specified in config for lagoon {lagoon_id}")

    try:
        tz = ZoneInfo(lagoon_timezone)
    except Exception as exc:
        raise ValueError(f"Invalid timezone {lagoon_timezone} for lagoon {lagoon_id}") from exc

    sender = get_backend_sender(cfg, root_cfg)
    send_queue: Queue | None = None

    send_queue_maxsize = int(get_runtime_option(cfg, root_cfg, "send_queue_maxsize", 1000))
    send_queue_maxsize = max(1, send_queue_maxsize)
    send_queue_full_policy = str(
        get_runtime_option(cfg, root_cfg, "send_queue_full_policy", "drop_newest")
    ).strip().lower()
    if send_queue_full_policy not in {"drop_newest", "drop_oldest", "block"}:
        logger.warning(
            "[COLLECTOR CONFIG] lagoon=%s reason=invalid_queue_policy value=%s fallback=drop_newest",
            lagoon_id,
            send_queue_full_policy,
        )
        send_queue_full_policy = "drop_newest"

    spool_on_send_fail = as_bool(get_runtime_option(cfg, root_cfg, "spool_on_send_fail", True), True)
    log_every_n_cycles = int(get_runtime_option(cfg, root_cfg, "log_every_n_cycles", 10))
    log_every_n_sends = int(get_runtime_option(cfg, root_cfg, "log_every_n_sends", 100))
    replay_batch_size = int(
        get_runtime_option(cfg, root_cfg, "replay_spool_batch_size", 50)
    )
    retry_attempts = int(
        get_runtime_option(cfg, root_cfg, "send_retry_attempts", 2)
    )
    retry_backoff_base_sec = float(
        get_runtime_option(cfg, root_cfg, "send_retry_backoff_base_sec", 1.0)
    )
    retry_backoff_max_sec = float(
        get_runtime_option(cfg, root_cfg, "send_retry_backoff_max_sec", 8.0)
    )
    startup_jitter_max_sec = max(
        0.0,
        float(get_runtime_option(cfg, root_cfg, "startup_jitter_max_sec", min(0.25, poll))),
    )
    enable_state_events = as_bool(get_runtime_option(cfg, root_cfg, "enable_state_events", True), True)

    if sender:
        send_queue = Queue(maxsize=send_queue_maxsize)
        sender_thread = threading.Thread(
            target=sender_worker_loop,
            args=(
                lagoon_id,
                sender,
                send_queue,
                spool_on_send_fail,
                log_every_n_sends,
                replay_batch_size,
                retry_attempts,
                retry_backoff_base_sec,
                retry_backoff_max_sec,
            ),
            name=f"sender-{lagoon_id}",
            daemon=True,
        )
        sender_thread.start()

    boolean_detector = BooleanEventDetector()
    state_detector = StateEventDetector()
    tot_normalizer = TotDeltaNormalizer()

    event_tags = cfg.get("event_tags", {}) or {}

    if source == "rockwell":
        rockwell_cfg = cfg["rockwell"]
        reader = RockwellSessionReader(
            ip=rockwell_cfg["ip"],
            slot=int(rockwell_cfg.get("slot", 0)),
            tag_map=cfg["tags"],
            force_reconnect_every_sec=int(cfg.get("force_reconnect_every_sec", 3600)),
            max_consecutive_fails=int(cfg.get("max_consecutive_fails", 10)),
            timeout_sec=float(rockwell_cfg.get("timeout_sec", 5.0)),
        )
    elif source == "siemens":
        siemens_cfg = cfg["siemens"]
        reader = SiemensSessionReader(
            endpoint=siemens_cfg["opc_server_url"],
            tag_map=cfg["tags"],
            timeout_sec=float(siemens_cfg.get("timeout_sec", 4)),
            username=siemens_cfg.get("username"),
            password=siemens_cfg.get("password"),
        )
    else:
        raise ValueError(f"Unsupported source: {source}")

    startup_jitter = random.uniform(0.0, startup_jitter_max_sec)
    if startup_jitter > 0:
        time.sleep(startup_jitter)

    logger.info(
        "[COLLECTOR START] lagoon=%s source=%s poll=%.2fs queue=%s policy=%s",
        lagoon_id,
        source,
        poll,
        send_queue_maxsize if send_queue else 0,
        send_queue_full_policy if send_queue else "disabled",
    )

    cycle_count = 0
    dropped_count = 0
    next_tick = time.perf_counter()

    while True:
        cycle_count += 1
        cycle_start = time.perf_counter()
        tags: dict[str, Any] = {}
        all_events: list[dict] = []
        timestamp_utc = utc_now()

        try:
            raw_tags = reader.read_once()
            tags = dict(raw_tags or {})
        except Exception as exc:
            logger.error("[COLLECTOR READ ERROR] lagoon=%s source=%s err=%s", lagoon_id, source, exc)

        if tags:
            if TOT_TAG in tags:
                key = f"{lagoon_id}:{TOT_TAG}"
                delta = tot_normalizer.compute(key, tags.get(TOT_TAG))
                tags[DELTA_TAG] = delta

            payload = NormalizedPayload(
                lagoon_id=lagoon_id,
                source=source,
                timestamp=timestamp_utc,
                tags=tags,
            )

            if event_tags:
                all_events.extend(
                    boolean_detector.process(
                        lagoon_id=lagoon_id,
                        tags=tags,
                        ts=payload.timestamp,
                        event_tags=event_tags,
                    )
                )

            if enable_state_events:
                all_events.extend(
                    state_detector.process(
                        lagoon_id=lagoon_id,
                        tags=tags,
                        ts=payload.timestamp,
                    )
                )

            if all_events:
                payload.events = all_events

            if sender and send_queue:
                enqueued = enqueue_payload(send_queue, payload, send_queue_full_policy)
                if not enqueued:
                    dropped_count += 1
                    if spool_on_send_fail:
                        spool_payload(payload)
        else:
            if log_every_n_cycles > 0 and cycle_count % log_every_n_cycles == 0:
                logger.warning("[COLLECTOR EMPTY] lagoon=%s source=%s", lagoon_id, source)

        if log_every_n_cycles > 0 and cycle_count % log_every_n_cycles == 0:
            elapsed = time.perf_counter() - cycle_start
            queue_depth = send_queue.qsize() if send_queue else 0
            local_ts = timestamp_utc.astimezone(tz).isoformat()
            logger.debug(
                "[COLLECTOR CYCLE] lagoon=%s source=%s tags=%s events=%s queue=%s dropped=%s elapsed=%.1fms utc=%s local=%s",
                lagoon_id,
                source,
                len(tags),
                len(all_events),
                queue_depth,
                dropped_count,
                elapsed * 1000,
                timestamp_utc.isoformat(),
                local_ts,
            )

        next_tick += poll
        sleep_for = next_tick - time.perf_counter()
        if sleep_for > 0:
            time.sleep(sleep_for)
        else:
            next_tick = time.perf_counter()


def main(config_path: str):
    plc_configs, root_cfg = load_plc_configs(config_path)
    migrated = jsonl_buffer.migrate_legacy_buffer()
    if migrated:
        logger.info("[COLLECTOR STARTUP] migrated_spool_lagoons=%s", migrated)

    if len(plc_configs) == 1:
        run_one_plc(plc_configs[0], root_cfg)
        return

    logger.info("[COLLECTOR STARTUP] workers=%s", len(plc_configs))

    with ThreadPoolExecutor(max_workers=len(plc_configs), thread_name_prefix="plc") as ex:
        futures = [ex.submit(run_one_plc, cfg, root_cfg) for cfg in plc_configs]

        for future in futures:
            try:
                future.result()
            except Exception as exc:
                logger.error("[COLLECTOR WORKER ERROR] err=%s", exc)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    main(args.config)
