import json
import os
import structlog
from datetime import datetime, timedelta
from typing import Any, Dict

from sqlalchemy.exc import SQLAlchemyError
from scrapy.exceptions import DropItem

from .items import AngaliaItem, JobItem, ProductItem
from .storage.db import get_session
from .storage.models import Item, ItemHistory, AlertSent

log = structlog.get_logger(__name__)

# ----------------------------------------------------------------------
# Helper utilities
# ----------------------------------------------------------------------


def _serialize_item(item: AngaliaItem) -> Dict[str, Any]:
    """Convert an AngaliaItem (or subclass) into a JSON‑serialisable dict."""
    data = item.__dict__.copy()
    # Convert datetime objects to isoformat for JSON persistence
    for key, value in data.items():
        if isinstance(value, datetime):
            data[key] = value.isoformat()
    return data


# ----------------------------------------------------------------------
# Pipelines
# ----------------------------------------------------------------------


class ValidationPipeline:
    """Drop items missing any of the required base fields."""

    def process_item(self, item: AngaliaItem, spider):
        missing = []
        for field in ("source", "external_id", "url", "scraped_at", "content_hash"):
            if getattr(item, field, None) in (None, ""):
                missing.append(field)
        if missing:
            log.warning(
                "dropping_item_missing_fields",
                spider=spider.name,
                missing=missing,
                external_id=getattr(item, "external_id", None),
            )
            raise DropItem(f"Missing required fields: {missing}")
        return item


class DeduplicationPipeline:
    """
    Skip items whose content_hash has been seen in the recent N runs.
    N is configurable via env var DEDUP_WINDOW_DAYS (default 3).
    """

    def __init__(self):
        window_days = int(os.getenv("DEDUP_WINDOW_DAYS", "3"))
        self.cutoff = datetime.utcnow() - timedelta(days=window_days)

    def process_item(self, item: AngaliaItem, spider):
        try:
            with get_session() as session:
                recent = (
                    session.query(Item.content_hash)
                    .filter(Item.content_hash == item.content_hash)
                    .filter(Item.last_seen >= self.cutoff)
                    .first()
                )
            if recent:
                log.info(
                    "dedup_item",
                    spider=spider.name,
                    external_id=item.external_id,
                    source=item.source,
                )
                raise DropItem("Duplicate content_hash")
        except SQLAlchemyError as exc:
            log.error("dedup_error", error=str(exc))
            # Do not block the pipeline – let the item continue.
        return item


class SQLiteStorePipeline:
    """
    Persist items to SQLite via SQLAlchemy.
    Creates or updates a row; records first_seen/last_seen timestamps.
    Any DB errors are logged and the pipeline continues.
    """

    def process_item(self, item: AngaliaItem, spider):
        try:
            with get_session() as session:
                existing = (
                    session.query(Item)
                    .filter_by(source=item.source, external_id=item.external_id)
                    .one_or_none()
                )
                serialized = json.dumps(_serialize_item(item))

                now = datetime.utcnow()
                if existing:
                    existing.last_seen = now
                    existing.data = serialized
                else:
                    new = Item(
                        source=item.source,
                        external_id=item.external_id,
                        url=item.url,
                        data=serialized,
                        content_hash=item.content_hash,
                        first_seen=now,
                        last_seen=now,
                    )
                    session.add(new)
                session.commit()
        except SQLAlchemyError as exc:
            log.error("sqlite_store_error", error=str(exc), item=str(item))
        return item


class DiffPipeline:
    """
    Compare the incoming item with the most recent stored version.
    Emits a list of dict change events into the spider’s `self.crawler.stats`
    for later consumption by the notifier.
    """

    def __init__(self):
        from .diff.engine import diff

        self.diff_func = diff

    def process_item(self, item: AngaliaItem, spider):
        try:
            with get_session() as session:
                stored = (
                    session.query(Item)
                    .filter_by(source=item.source, external_id=item.external_id)
                    .order_by(Item.last_seen.desc())
                    .first()
                )
                if stored:
                    old_data = json.loads(stored.data)
                    old_item = self._reconstruct(old_data, item.__class__)
                    changes = self.diff_func(old_item, item)
                else:
                    # New item – emit a single NEW event
                    changes = [
                        {
                            "type": "NEW",
                            "source": item.source,
                            "external_id": item.external_id,
                            "field": None,
                            "old": None,
                            "new": _serialize_item(item),
                            "url": item.url,
                        }
                    ]
                if changes:
                    spider.crawler.stats.inc_value("change_events", len(changes))
                    key = "change_events_list"
                    existing = spider.crawler.stats.get_value(key, [])
                    existing.extend(changes)
                    spider.crawler.stats.set_value(key, existing)
        except Exception as exc:
            log.error("diff_error", error=str(exc), item=str(item))
        return item

    @staticmethod
    def _reconstruct(data: Dict[str, Any], cls):
        """Re‑create an item instance from stored JSON."""
        if cls == JobItem:
            return JobItem(**{k: v for k, v in data.items() if k in JobItem.__annotations__})
        elif cls == ProductItem:
            return ProductItem(**{k: v for k, v in data.items() if k in ProductItem.__annotations__})
        else:
            raise ValueError(f"Unsupported class for reconstruction: {cls}")
