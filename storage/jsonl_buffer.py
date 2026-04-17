from __future__ import annotations

import json
import os
import re
import threading
from pathlib import Path
from typing import Callable, TextIO

_BUFFER_LOCK = threading.Lock()
DEFAULT_SPOOL_DIR = Path("data/spool")
DEFAULT_LEGACY_BUFFER_PATH = Path("data/buffer.jsonl")
ReplayAction = bool | str


def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _safe_lagoon_id(lagoon_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", lagoon_id.strip())
    return safe or "unknown"


def _iter_nonempty_lines(handle: TextIO):
    for raw_line in handle:
        line = raw_line.rstrip("\n")
        if line.strip():
            yield line


def _copy_nonempty_lines(source: Path, destination: TextIO) -> int:
    if not source.exists():
        return 0

    copied = 0
    with source.open("r", encoding="utf-8") as handle:
        for line in _iter_nonempty_lines(handle):
            destination.write(line)
            destination.write("\n")
            copied += 1

    return copied


def _normalize_replay_action(result: ReplayAction) -> str:
    if result is True or result == "sent":
        return "sent"
    if result == "drop":
        return "drop"
    return "keep"


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

        temp_path = legacy_file.with_name(f"{legacy_file.name}.tmp")
        retained_count = 0
        target_handles: dict[str, TextIO] = {}

        try:
            with (
                legacy_file.open("r", encoding="utf-8") as source,
                temp_path.open("w", encoding="utf-8") as retained_handle,
            ):
                for line in _iter_nonempty_lines(source):
                    lagoon_id = _extract_lagoon_id(line)
                    if not lagoon_id:
                        retained_handle.write(line)
                        retained_handle.write("\n")
                        retained_count += 1
                        continue

                    handle = target_handles.get(lagoon_id)
                    if handle is None:
                        target_path = spool_path_for_lagoon(lagoon_id, base_dir=base_dir)
                        _ensure_parent_dir(target_path)
                        handle = target_path.open("a", encoding="utf-8")
                        target_handles[lagoon_id] = handle

                    handle.write(line)
                    handle.write("\n")
                    migrated_counts[lagoon_id] = migrated_counts.get(lagoon_id, 0) + 1

                retained_handle.flush()
                os.fsync(retained_handle.fileno())

            for handle in target_handles.values():
                handle.flush()
                os.fsync(handle.fileno())
        finally:
            for handle in target_handles.values():
                handle.close()

        if retained_count:
            os.replace(temp_path, legacy_file)
        else:
            temp_path.unlink(missing_ok=True)
            legacy_file.unlink(missing_ok=True)

    return migrated_counts


def replay_for_lagoon(
    lagoon_id: str,
    send_payload: Callable[[dict], ReplayAction],
    max_items: int = 50,
    base_dir: str | Path = DEFAULT_SPOOL_DIR,
) -> tuple[int, int, int]:
    spool_path = spool_path_for_lagoon(lagoon_id, base_dir=base_dir)
    work_path = spool_path.with_suffix(".work")
    remaining_path = spool_path.with_name(f"{spool_path.name}.remaining")
    merged_path = spool_path.with_name(f"{spool_path.name}.tmp")

    with _BUFFER_LOCK:
        if work_path.exists():
            active_work_path = work_path
        elif not spool_path.exists() or spool_path.stat().st_size == 0:
            return (0, 0, 0)
        else:
            os.replace(spool_path, work_path)
            active_work_path = work_path

    sent = 0
    dropped = 0
    pending_work = 0

    try:
        with (
            active_work_path.open("r", encoding="utf-8") as source,
            remaining_path.open("w", encoding="utf-8") as remaining_handle,
        ):
            copy_only = False
            for line in _iter_nonempty_lines(source):
                if copy_only or sent >= max_items:
                    remaining_handle.write(line)
                    remaining_handle.write("\n")
                    pending_work += 1
                    continue

                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    dropped += 1
                    continue

                action = _normalize_replay_action(send_payload(payload))
                if action == "sent":
                    sent += 1
                    continue
                if action == "drop":
                    dropped += 1
                    continue

                remaining_handle.write(line)
                remaining_handle.write("\n")
                pending_work += 1
                copy_only = True

            remaining_handle.flush()
            os.fsync(remaining_handle.fileno())
    except FileNotFoundError:
        return (0, 0, 0)

    with _BUFFER_LOCK:
        pending_total = 0
        _ensure_parent_dir(merged_path)
        with merged_path.open("w", encoding="utf-8") as merged_handle:
            if pending_work:
                pending_total += _copy_nonempty_lines(remaining_path, merged_handle)
            if spool_path.exists():
                pending_total += _copy_nonempty_lines(spool_path, merged_handle)
            merged_handle.flush()
            os.fsync(merged_handle.fileno())

        if pending_total:
            os.replace(merged_path, spool_path)
        else:
            merged_path.unlink(missing_ok=True)
            spool_path.unlink(missing_ok=True)

        active_work_path.unlink(missing_ok=True)
        remaining_path.unlink(missing_ok=True)

    return (sent, pending_total, dropped)
