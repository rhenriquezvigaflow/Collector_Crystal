from __future__ import annotations

import json
import os
import re
import threading
from pathlib import Path
from typing import Callable

_BUFFER_LOCK = threading.Lock()
DEFAULT_SPOOL_DIR = Path("data/spool")
DEFAULT_LEGACY_BUFFER_PATH = Path("data/buffer.jsonl")


def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _safe_lagoon_id(lagoon_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", lagoon_id.strip())
    return safe or "unknown"


def spool_path_for_lagoon(
    lagoon_id: str,
    base_dir: str | Path = DEFAULT_SPOOL_DIR,
) -> Path:
    return Path(base_dir) / f"{_safe_lagoon_id(lagoon_id)}.jsonl"


def append(payload_json: str, path: str = "data/buffer.jsonl") -> None:
    target_path = Path(path)
    _ensure_parent_dir(target_path)

    with _BUFFER_LOCK:
        with target_path.open("a", encoding="utf-8") as handle:
            handle.write(payload_json)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())


def append_for_lagoon(
    lagoon_id: str,
    payload_json: str,
    base_dir: str | Path = DEFAULT_SPOOL_DIR,
) -> Path:
    target_path = spool_path_for_lagoon(lagoon_id, base_dir=base_dir)
    _ensure_parent_dir(target_path)

    with _BUFFER_LOCK:
        with target_path.open("a", encoding="utf-8") as handle:
            handle.write(payload_json)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

    return target_path


def _extract_lagoon_id(payload_json: str) -> str | None:
    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError:
        return None

    lagoon_id = payload.get("lagoon_id")
    if not isinstance(lagoon_id, str) or not lagoon_id.strip():
        return None
    return lagoon_id.strip()


def migrate_legacy_buffer(
    legacy_path: str | Path = DEFAULT_LEGACY_BUFFER_PATH,
    base_dir: str | Path = DEFAULT_SPOOL_DIR,
) -> dict[str, int]:
    legacy_file = Path(legacy_path)
    if not legacy_file.exists() or legacy_file.stat().st_size == 0:
        return {}

    migrated_counts: dict[str, int] = {}

    with _BUFFER_LOCK:
        if not legacy_file.exists() or legacy_file.stat().st_size == 0:
            return {}

        with legacy_file.open("r", encoding="utf-8") as handle:
            lines = [line.rstrip("\n") for line in handle if line.strip()]

        grouped: dict[str, list[str]] = {}
        retained: list[str] = []
        for line in lines:
            lagoon_id = _extract_lagoon_id(line)
            if not lagoon_id:
                retained.append(line)
                continue
            grouped.setdefault(lagoon_id, []).append(line)

        for lagoon_id, lagoon_lines in grouped.items():
            target_path = spool_path_for_lagoon(lagoon_id, base_dir=base_dir)
            _ensure_parent_dir(target_path)
            with target_path.open("a", encoding="utf-8") as handle:
                for line in lagoon_lines:
                    handle.write(line)
                    handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            migrated_counts[lagoon_id] = len(lagoon_lines)

        if retained:
            temp_path = legacy_file.with_suffix(".tmp")
            with temp_path.open("w", encoding="utf-8") as handle:
                for line in retained:
                    handle.write(line)
                    handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, legacy_file)
        else:
            legacy_file.unlink(missing_ok=True)

    return migrated_counts


def replay_for_lagoon(
    lagoon_id: str,
    send_payload: Callable[[dict], bool],
    max_items: int = 50,
    base_dir: str | Path = DEFAULT_SPOOL_DIR,
) -> tuple[int, int, int]:
    spool_path = spool_path_for_lagoon(lagoon_id, base_dir=base_dir)
    work_path = spool_path.with_suffix(".work")

    with _BUFFER_LOCK:
        if work_path.exists():
            active_work_path = work_path
        elif not spool_path.exists() or spool_path.stat().st_size == 0:
            return (0, 0, 0)
        else:
            os.replace(spool_path, work_path)
            active_work_path = work_path

    try:
        with active_work_path.open("r", encoding="utf-8") as handle:
            lines = [line.rstrip("\n") for line in handle if line.strip()]
    except FileNotFoundError:
        return (0, 0, 0)

    sent = 0
    dropped = 0
    remaining: list[str] = []

    for index, line in enumerate(lines):
        if sent >= max_items:
            remaining.append(line)
            continue

        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            dropped += 1
            continue

        if send_payload(payload):
            sent += 1
            continue

        remaining.append(line)
        remaining.extend(lines[index + 1 :])
        break

    with _BUFFER_LOCK:
        newer_lines: list[str] = []
        if spool_path.exists():
            with spool_path.open("r", encoding="utf-8") as handle:
                newer_lines = [line.rstrip("\n") for line in handle if line.strip()]

        merged_lines = [line for line in remaining if line]
        merged_lines.extend(newer_lines)

        if merged_lines:
            temp_path = spool_path.with_suffix(".tmp")
            _ensure_parent_dir(temp_path)
            with temp_path.open("w", encoding="utf-8") as handle:
                for line in merged_lines:
                    handle.write(line)
                    handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, spool_path)
        else:
            spool_path.unlink(missing_ok=True)

        active_work_path.unlink(missing_ok=True)

    return (sent, len(merged_lines), dropped)
