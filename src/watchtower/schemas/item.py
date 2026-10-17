"""Pydantic schemas for scraped items and item-level changes."""

from datetime import UTC, datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ScrapedItem(BaseModel):
    """Canonical model for scraped job and product records."""

    model_config = ConfigDict(from_attributes=True)

    site: str
    external_id: str
    url: str
    title: str
    company: Optional[str] = None  # Company for jobs or seller for e-commerce
    price_kes: Optional[float] = None
    currency: str = "KES"
    location: Optional[str] = None
    posted_at: Optional[str] = None  # ISO format string
    category: Optional[str] = None
    raw: Dict[str, Any] = Field(default_factory=dict)
    scraped_at: datetime = Field(default_factory=utc_now)


class PriceChange(BaseModel):
    """Payload representing a detected price change."""

    model_config = ConfigDict(from_attributes=True)

    old: Optional[float] = None
    new: Optional[float] = None
    pct: float
    direction: str  # 'price_drop' or 'price_increase'


class NewListing(BaseModel):
    """Payload representing a detected new item listing."""

    model_config = ConfigDict(from_attributes=True)

    site: str
    external_id: str
    title: str
    url: str
    company: Optional[str] = None
    price_kes: Optional[float] = None
    location: Optional[str] = None
    category: Optional[str] = None
