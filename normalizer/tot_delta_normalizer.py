from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class TotDeltaNormalizer:
    """
    Convierte un acumulativo (TOT) a incrementos (DELTA) detectando resets:
      - primera lectura => delta 0
      - si current < prev => reset => delta = current
      - si current >= prev => delta = current - prev
    """
    prev: Dict[str, float] = field(default_factory=dict)

    def compute(self, key: str, current: Optional[float]) -> float:
        if current is None:
            return 0.0

        try:
            cur = float(current)
        except (TypeError, ValueError):
            return 0.0

        if cur < 0:
            return 0.0

        previous = self.prev.get(key)
        if previous is None:
            self.prev[key] = cur
            return 0.0

        if cur < previous:
            delta = cur  # reset
        else:
            delta = cur - previous

        self.prev[key] = cur
        return max(delta, 0.0)
