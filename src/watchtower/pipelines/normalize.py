"""Pipeline for data cleansing, price normalization to KES, and date parsing."""

import re
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, Optional

from dateutil import parser as date_parser

from watchtower.logging import get_logger

logger = get_logger(__name__)


def clean_text(text: Optional[str]) -> Optional[str]:
    """Strip excess whitespace and unwanted control characters."""
    if not text:
        return None
    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned if cleaned else None


def normalize_price(price_raw: Any) -> Optional[float]:
    """Normalize raw price string/number to clean float KES."""
    if price_raw is None:
        return None
    if isinstance(price_raw, (int, float)):
        return float(price_raw)

    text = str(price_raw).strip()
    if not text:
        return None

    # Handle range e.g. "KSh 1,500 - KSh 3,000", take the first price
    if "-" in text:
        text = text.split("-")[0].strip()

    # Remove currency prefixes, commas, and other non-digits except dot
    # e.g. "KSh 12,999.00" -> "12999.00"
    cleaned = re.sub(r"[^\d.]", "", text)
    if not cleaned:
        return None

    # Handle cases with multiple dots (e.g. thousands separated by dot)
    if cleaned.count(".") > 1:
        parts = cleaned.split(".")
        cleaned = "".join(parts[:-1]) + "." + parts[-1]

    try:
        val = float(cleaned)
        return round(val, 2)
    except (ValueError, TypeError):
        return None


def normalize_datetime(date_raw: Any) -> Optional[str]:
    """Normalize raw date or relative string to ISO 8601 UTC string."""
    if not date_raw:
        return None
    if isinstance(date_raw, datetime):
        if date_raw.tzinfo is not None:
            return date_raw.astimezone(UTC).replace(tzinfo=None).isoformat()
        return date_raw.isoformat()

    text = str(date_raw).strip()
    if not text:
        return None

    now = datetime.now(UTC).replace(tzinfo=None)
    lower = text.lower()

    # Relative timestamps
    if "just now" in lower or "today" in lower:
        return now.isoformat()
    if "yesterday" in lower:
        return (now - timedelta(days=1)).isoformat()

    match_hours = re.search(r"(\d+)\s*(?:hour|hr)", lower)
    if match_hours:
        hours = int(match_hours.group(1))
        return (now - timedelta(hours=hours)).isoformat()

    match_days = re.search(r"(\d+)\s*(?:day)", lower)
    if match_days:
        days = int(match_days.group(1))
        return (now - timedelta(days=days)).isoformat()

    match_mins = re.search(r"(\d+)\s*(?:min|minute)", lower)
    if match_mins:
        mins = int(match_mins.group(1))
        return (now - timedelta(minutes=mins)).isoformat()

    # Standard date parsing via dateutil
    try:
        dt = date_parser.parse(text)
        if dt.tzinfo is not None:
            dt = dt.astimezone(UTC).replace(tzinfo=None)
        return dt.isoformat()
    except (ValueError, OverflowError, TypeError):
        logger.warning("date_parsing_failed", raw_date=text)
        return None


class NormalizePipeline:
    """Scrapy pipeline stage for sanitizing and normalizing item fields."""

    def process_item(self, item: Dict[str, Any], spider: Any) -> Dict[str, Any]:
        """Normalize all string and numerical fields."""
        item["title"] = clean_text(item.get("title")) or "Untitled"
        item["company"] = clean_text(item.get("company"))
        item["location"] = clean_text(item.get("location"))
        item["category"] = clean_text(item.get("category"))
        item["currency"] = "KES"
        item["price_kes"] = normalize_price(item.get("price_kes"))
        item["posted_at"] = normalize_datetime(item.get("posted_at"))

        if "url" in item and item["url"]:
            item["url"] = item["url"].strip()
        if "external_id" in item and item["external_id"]:
            item["external_id"] = str(item["external_id"]).strip()

        return item
