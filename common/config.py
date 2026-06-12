from __future__ import annotations

import os
from typing import Any

import yaml

VALID_PRODUCT_TYPES = {"crystal", "small"}


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
            included_config = load_config(included_path)
            include_overrides = {
                key: value
                for key, value in entry.items()
                if key != "include"
            }
            plc_configs.append({**included_config, **include_overrides})
        else:
            plc_configs.append(entry)

    return plc_configs, root


def normalize_product_type(value: Any, *, lagoon_id: str | None = None) -> str:
    product_type = str(value or "crystal").strip().lower()
    if product_type not in VALID_PRODUCT_TYPES:
        lagoon_label = lagoon_id or "-"
        allowed = ", ".join(sorted(VALID_PRODUCT_TYPES))
        raise ValueError(
            f"Invalid product_type {product_type!r} for lagoon {lagoon_label}; "
            f"expected one of: {allowed}"
        )
    return product_type


def resolve_product_type(cfg: dict, root_cfg: dict) -> str:
    return normalize_product_type(
        cfg.get("product_type") or root_cfg.get("product_type") or "crystal",
        lagoon_id=str(cfg.get("lagoon_id") or ""),
    )
