from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ChangeEvent:
    """A single change detected between two items."""
    type: str  # NEW, PRICE_DROP, PRICE_RISE, UPDATED, REMOVED
    source: str
    external_id: str
    field: str | None  # None for NEW/REMOVED events
    old: Any | None  # previous value (or None)
    new: Any | None  # new value (or None)
    url: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key)
