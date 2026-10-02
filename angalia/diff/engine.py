from typing import List, Any, Dict
from .models import ChangeEvent
from ..items import AngaliaItem, JobItem, ProductItem


def diff(old_item: AngaliaItem, new_item: AngaliaItem) -> List[Dict[str, Any]]:
    """
    Pure diff function returning a list of dict change events.
    Rules:
    - If old_item is None → NEW
    - If new_item is None → REMOVED
    - For ProductItem: detect price direction.
    - For any other field changes → UPDATED.
    """
    events: List[Dict[str, Any]] = []

    if old_item is None:
        events.append(
            {
                "type": "NEW",
                "source": new_item.source,
                "external_id": new_item.external_id,
                "field": None,
                "old": None,
                "new": new_item,
                "url": new_item.url,
            }
        )
        return events

    if new_item is None:
        events.append(
            {
                "type": "REMOVED",
                "source": old_item.source,
                "external_id": old_item.external_id,
                "field": None,
                "old": old_item,
                "new": None,
                "url": old_item.url,
            }
        )
        return events

    # Helper to compare scalar fields safely
    def _field_changed(f):
        return getattr(old_item, f, None) != getattr(new_item, f, None)

    # Price change detection (only for ProductItem)
    if isinstance(old_item, ProductItem) and isinstance(new_item, ProductItem):
        if old_item.price != new_item.price:
            price_event_type = "PRICE_DROP" if new_item.price < old_item.price else "PRICE_RISE"
            events.append(
                {
                    "type": price_event_type,
                    "source": new_item.source,
                    "external_id": new_item.external_id,
                    "field": "price",
                    "old": old_item.price,
                    "new": new_item.price,
                    "url": new_item.url,
                }
            )
    # Detect any other field differences (excluding the common base fields)
    compare_fields = set(new_item.__dataclass_fields__) - {"source", "external_id", "url", "scraped_at", "content_hash"}
    for field in compare_fields:
        if _field_changed(field):
            events.append(
                {
                    "type": "UPDATED",
                    "source": new_item.source,
                    "external_id": new_item.external_id,
                    "field": field,
                    "old": getattr(old_item, field, None),
                    "new": getattr(new_item, field, None),
                    "url": new_item.url,
                }
            )
    return events
