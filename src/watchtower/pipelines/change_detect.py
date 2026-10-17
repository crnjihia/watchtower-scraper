"""Change detection logic for new listings and price fluctuations."""

from typing import Any, Dict, Optional, Tuple

from watchtower.config import get_settings
from watchtower.db.models import ChangeKind, Item, ItemSnapshot
from watchtower.logging import get_logger

logger = get_logger(__name__)


def detect_item_change(
    existing_item: Optional[Item],
    latest_snapshot: Optional[ItemSnapshot],
    new_price: Optional[float],
    min_price_delta_pct: Optional[float] = None,
) -> Optional[Tuple[ChangeKind, Dict[str, Any]]]:
    """Detect whether a scraped item represents a new listing or price movement.

    Returns:
        (ChangeKind, diff_dict) if a meaningful change was detected, else None.
    """
    settings = get_settings()
    threshold = (
        min_price_delta_pct
        if min_price_delta_pct is not None
        else settings.MIN_PRICE_DELTA_PCT
    )

    # 1. New listing detection
    if existing_item is None:
        return ChangeKind.NEW_LISTING, {
            "price_kes": new_price,
            "type": "new_listing",
        }

    # 2. Price change detection
    if latest_snapshot is None or latest_snapshot.price_kes is None:
        if new_price is not None:
            # First recorded price for an existing item
            return ChangeKind.UPDATED, {
                "old": None,
                "new": new_price,
                "pct": 100.0,
                "note": "Initial price recorded",
            }
        return None

    old_price = latest_snapshot.price_kes
    if new_price is None or old_price == new_price:
        return None

    if old_price > 0:
        delta = new_price - old_price
        pct = round(abs(delta) / old_price * 100.0, 2)
    else:
        delta = new_price
        pct = 100.0

    if pct >= threshold:
        if new_price < old_price:
            return ChangeKind.PRICE_DROP, {
                "old": old_price,
                "new": new_price,
                "pct": pct,
            }
        else:
            return ChangeKind.PRICE_INCREASE, {
                "old": old_price,
                "new": new_price,
                "pct": pct,
            }

    return None


class ChangeDetectionPipeline:
    """Pipeline stage that attaches detected changes to the item dictionary."""

    def process_item(self, item: Dict[str, Any], spider: Any) -> Dict[str, Any]:
        """Pass-through for change detection metadata."""
        return item
