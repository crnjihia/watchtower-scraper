from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ChangeEvent:
    """A single change detected between two items."""
    type: str               # NEW, PRICE_DROP, PRICE_RISE, UPDATED, REMOVED
    source: str
    external_id: str
    field: Optional[str]   # None for NEW/REMOVED events
    old: Optional[object] # previous value (or None)
    new: Optional[object] # new value (or None)
    url: str
