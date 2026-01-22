from pydantic import BaseModel
from typing import Dict, Any, Literal
from datetime import datetime

class NormalizedPayload(BaseModel):
    plant_id: int
    source: Literal["rockwell", "siemens"]
    timestamp: datetime      # UTC
    tags: Dict[str, Any]
