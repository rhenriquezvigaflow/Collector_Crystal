from __future__ import annotations

import random
from typing import Any


class SimulatedTagReader:
    def __init__(
        self,
        tag_specs: dict[str, Any],
        *,
        seed: int | None = None,
    ) -> None:
        self.tag_specs = tag_specs
        self._random = random.Random(seed)
        self._state: dict[str, Any] = {}

    def read_once(self) -> dict[str, Any]:
        return {
            tag_id: self._next_value(tag_id, spec)
            for tag_id, spec in self.tag_specs.items()
        }

    def _next_value(self, tag_id: str, spec: Any) -> Any:
        if not isinstance(spec, dict):
            return spec

        value_type = str(spec.get("type") or "float").strip().lower()
        if value_type == "bool":
            return self._next_bool(tag_id, spec)
        if value_type in {"state", "choice"}:
            return self._next_choice(tag_id, spec)
        if value_type == "int":
            return self._next_int(tag_id, spec)
        return self._next_float(tag_id, spec)

    def _next_float(self, tag_id: str, spec: dict[str, Any]) -> float:
        min_value = float(spec.get("min", 0.0))
        max_value = float(spec.get("max", 100.0))
        decimals = int(spec.get("decimals", 2))
        span = max(max_value - min_value, 0.0)
        step = float(spec.get("step", span / 12 if span else 1.0))

        current = self._state.get(tag_id)
        if not isinstance(current, (int, float)):
            current = self._random.uniform(min_value, max_value)
        else:
            current = float(current) + self._random.uniform(-step, step)

        next_value = min(max(float(current), min_value), max_value)
        self._state[tag_id] = next_value
        return round(next_value, decimals)

    def _next_int(self, tag_id: str, spec: dict[str, Any]) -> int:
        min_value = int(spec.get("min", 0))
        max_value = int(spec.get("max", 100))
        step = max(1, int(spec.get("step", 1)))

        current = self._state.get(tag_id)
        if not isinstance(current, int):
            current = self._random.randint(min_value, max_value)
        else:
            current += self._random.randint(-step, step)

        next_value = min(max(current, min_value), max_value)
        self._state[tag_id] = next_value
        return next_value

    def _next_bool(self, tag_id: str, spec: dict[str, Any]) -> bool:
        change_probability = float(spec.get("change_probability", 0.05))
        current = self._state.get(tag_id)
        if not isinstance(current, bool):
            current = bool(spec.get("initial", self._random.choice([True, False])))
        elif self._random.random() < change_probability:
            current = not current

        self._state[tag_id] = current
        return current

    def _next_choice(self, tag_id: str, spec: dict[str, Any]) -> Any:
        values = spec.get("values")
        if not isinstance(values, list) or not values:
            values = [0, 1]

        change_probability = float(spec.get("change_probability", 0.12))
        current = self._state.get(tag_id)
        if current not in values:
            current = self._random.choice(values)
        elif self._random.random() < change_probability:
            current = self._random.choice(values)

        self._state[tag_id] = current
        return current
