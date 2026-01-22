import time
import yaml
import argparse

from common.payload import NormalizedPayload
from common.time import utc_now
from common.logger import get_logger
from storage.jsonl_buffer import append
from workers.get_rockwell import RockwellSessionReader

logger = get_logger()

RECONNECT_DELAY = 5


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_rockwell(cfg: dict):
    plant_id = int(cfg["plant_id"])
    source = cfg["source"]
    poll = float(cfg.get("poll_seconds", 1))

    ip = cfg["rockwell"]["ip"]
    slot = int(cfg["rockwell"].get("slot", 0))
    tag_map = cfg["tags"]

    force_rotate = int(cfg.get("force_reconnect_every_sec", 3600))
    max_fails = int(cfg.get("max_consecutive_fails", 10))

    reader = RockwellSessionReader(
        ip=ip,
        slot=slot,
        tag_map=tag_map,
        force_reconnect_every_sec=force_rotate,
        max_consecutive_fails=max_fails,
    )

    logger.info(f"START plant={plant_id} source={source} plc={ip}/{slot} poll={poll}s tags={len(tag_map)}")

    while True:
        try:
            # Abrimos sesión (persistente)
            reader.connect()
            logger.info(f"CONNECTED plc={ip}/{slot}")

            # Loop de lectura a 1s
            while True:
                if reader.should_rotate():
                    raise Exception("FORCE_RECONNECT: session rotation")

                cycle_start = time.perf_counter()

                # 1) leer tags (batch)
                raw_tags = reader.read_once()

                # 2) payload normalizado
                payload = NormalizedPayload(
                    plant_id=plant_id,
                    source=source,
                    timestamp=utc_now(),
                    tags=raw_tags,
                )

                # 3) buffer local
                append(payload.model_dump_json())

                # 4) log con sample + timing
                elapsed = time.perf_counter() - cycle_start
                sample = list(raw_tags.items())[:4]
                logger.info(
                    f"OK plant={plant_id} ts={payload.timestamp.isoformat()} "
                    f"tags={len(raw_tags)} sample={sample} cycle={elapsed*1000:.1f}ms"
                )

                # 5) sleep para respetar poll_seconds
                sleep_for = poll - elapsed
                if sleep_for > 0:
                    time.sleep(sleep_for)

        except Exception as e:
            logger.warning(f"RECONNECT plant={plant_id} plc={ip}/{slot} reason={e} sleep={RECONNECT_DELAY}s")
            try:
                reader.close()
            except Exception:
                pass
            time.sleep(RECONNECT_DELAY)


def main(config_path: str):
    cfg = load_config(config_path)
    source = cfg.get("source")

    if source == "rockwell":
        run_rockwell(cfg)
    else:
        raise NotImplementedError("Only rockwell implemented for Día 3")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    main(args.config)
