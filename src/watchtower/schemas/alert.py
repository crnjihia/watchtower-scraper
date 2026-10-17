"""Alert payload schema for multi-channel notifications."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class AlertPayload(BaseModel):
    """Normalized payload ready for dispatch across notification channels."""

    model_config = ConfigDict(from_attributes=True)

    event_id: Optional[int] = None
    kind: str  # 'new_listing', 'price_drop', 'price_increase', 'removed', 'updated'
    site: str
    title: str
    url: str
    summary: str
    diff: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    company: Optional[str] = None
    location: Optional[str] = None
    price_kes: Optional[float] = None
