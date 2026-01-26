from typing import Dict, List
from datetime import datetime

class EventDetector:
    def __init__(self):
        self.last_states: Dict[tuple, bool] = {}

    def process(
        self,
        lagoon_id: str,
        tags: dict,
        ts: datetime,
        event_tags: dict,
    ) -> List[dict]:
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

            # primera vez → solo guardar
            if prev is None:
                self.last_states[key] = value
                continue

            # FALSE → TRUE (abrir)
            if prev is False and value is True:
                events.append({
                    "type": "OPEN",
                    "lagoon_id": lagoon_id,
                    "tag_id": tag_id,
                    "tag_label": label,
                    "ts": ts.isoformat(),
                })

            # TRUE → FALSE (cerrar)
            elif prev is True and value is False:
                events.append({
                    "type": "CLOSE",
                    "lagoon_id": lagoon_id,
                    "tag_id": tag_id,
                    "ts": ts.isoformat(),
                })

            self.last_states[key] = value

        return events
