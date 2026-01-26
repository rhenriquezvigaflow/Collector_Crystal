from pydantic import BaseModel
from datetime import datetime
from typing import Any, Optional, List


class ScadaEvent(BaseModel):
    type: str                 
    lagoon_id: str
    tag_id: str
    tag_label: Optional[str] = None
    ts: datetime


class NormalizedPayload(BaseModel):
    lagoon_id: str          
    source: str
    timestamp: datetime
    tags: dict[str, Any]

  
    events: Optional[List[ScadaEvent]] = None
