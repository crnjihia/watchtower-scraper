import json
import os
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from scrapy.exceptions import DropItem
from sqlalchemy.exc import SQLAlchemyError

from .diff.engine import diff
from .diff.models import ChangeEvent
from .items import AngaliaItem, JobItem, ProductItem
from .storage import db as storage_db
from .storage.models import Item, ItemHistory

logger = structlog.get_logger(__name__)


class ValidationPipeline:
    """Drop items missing any of the required fields."""

    def process_item(self, item: AngaliaItem, spider):
        missing = []
        base_fields = ("source", "external_id", "url", "scraped_at", "content_hash")
        for f in base_fields:
            if getattr(item, f, None) in (None, ""):
                missing.append(f)

        if isinstance(item, JobItem):
            if not getattr(item, "title", None):
                missing.append("title")
            if not getattr(item, "company", None):
                missing.append("company")

        elif isinstance(item, ProductItem):
            if not getattr(item, "name", None):
                missing.append("name")
            if getattr(item, "price", None) is None:
                missing.append("price")

        if missing:
            logger.warning(
                "dropping_item_missing_fields",
                spider=spider.name,
                missing=missing,
                external_id=getattr(item, "external_id", None),
            )
            raise DropItem(f"Missing required fields: {missing}")

        return item


class DeduplicationPipeline:
    """
    Skip items whose content_hash has been seen in recent N runs.
    Configurable via DEDUP_WINDOW_DAYS (default 3 days).
    """

    def __init__(self):
        window_days = int(os.getenv("DEDUP_WINDOW_DAYS", "3"))
        self.window_days = window_days

    def open_spider(self, spider):
        try:
            storage_db.init_db()
        except Exception as exc:
            logger.error("dedup_init_db_error", error=str(exc))

    def process_item(self, item: AngaliaItem, spider):
        cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=self.window_days)
        try:
            with storage_db.get_session() as session:
                recent = (
                    session.query(Item.id)
                    .filter(Item.content_hash == item.content_hash)
                    .filter(Item.last_seen >= cutoff)
                    .first()
                )
                if recent:
                    logger.info(
                        "dedup_item_skipped",
                        spider=spider.name,
                        external_id=item.external_id,
                        source=item.source,
                    )
                    raise DropItem(f"Duplicate content_hash seen within {self.window_days} days")
        except DropItem:
            raise
        except SQLAlchemyError as exc:
            logger.error("dedup_db_error", error=str(exc))
            # Continue on DB error to avoid blocking the scraper
        return item


class DiffPipeline:
    """
    Compare the incoming item with the stored version in SQLite.
    Emits ChangeEvent objects into the spider's crawler.stats and
    attaches them to the item for the storage pipeline to record in history.
    """

    def __init__(self):
        self.diff_func = diff

    def process_item(self, item: AngaliaItem, spider):
        changes: list[ChangeEvent] = []
        try:
            with storage_db.get_session() as session:
                stored = (
                    session.query(Item)
                    .filter_by(source=item.source, external_id=item.external_id)
                    .one_or_none()
                )
                if stored:
                    old_data = stored.data if isinstance(stored.data, dict) else json.loads(stored.data)
                    old_item = self._reconstruct(old_data, item.__class__)
                    changes = self.diff_func(old_item, item)
                else:
                    # Item not found in DB -> NEW item event
                    changes = self.diff_func(None, item)

            # Record events in spider stats for Celery / monitoring
            if changes:
                if hasattr(spider, "crawler") and hasattr(spider.crawler, "stats") and spider.crawler.stats:
                    spider.crawler.stats.inc_value("change_events", len(changes))
                    key = "change_events_list"
                    existing = spider.crawler.stats.get_value(key, []) or []
                    existing.extend([c.to_dict() if hasattr(c, "to_dict") else c for c in changes])
                    spider.crawler.stats.set_value(key, existing)

            # Attach to item for SQLiteStorePipeline to record into history table
            item._change_events = changes

        except Exception as exc:
            logger.error("diff_pipeline_error", error=str(exc), external_id=item.external_id)
            item._change_events = []

        return item

    @staticmethod
    def _reconstruct(data: dict[str, Any], cls):
        """Re-create item instance from stored JSON dictionary."""
        if cls == JobItem or issubclass(cls, JobItem):
            return JobItem.from_dict(data)
        elif cls == ProductItem or issubclass(cls, ProductItem):
            return ProductItem.from_dict(data)
        return cls(**data)


class SQLiteStorePipeline:
    """
    Persist items to SQLite via SQLAlchemy.
    - Table items: id, source, external_id, url, data (JSON), content_hash, first_seen, last_seen
    - Table history: id, item_id, field, old_value, new_value, changed_at
    Any DB errors are logged gracefully and the pipeline continues.
    """

    def open_spider(self, spider):
        try:
            storage_db.init_db()
        except Exception as exc:
            logger.error("sqlite_init_error", error=str(exc))

    def process_item(self, item: AngaliaItem, spider):

        try:
            with storage_db.get_session() as session:
                now = datetime.now(UTC).replace(tzinfo=None)
                serialized = item.to_dict() if hasattr(item, "to_dict") else item.__dict__

                existing = (
                    session.query(Item)
                    .filter_by(source=item.source, external_id=item.external_id)
                    .one_or_none()
                )

                if existing:
                    existing.last_seen = now
                    existing.url = item.url
                    existing.content_hash = item.content_hash
                    existing.data = serialized
                    item_id = existing.id
                else:
                    new_item = Item(
                        source=item.source,
                        external_id=item.external_id,
                        url=item.url,
                        data=serialized,
                        content_hash=item.content_hash,
                        first_seen=now,
                        last_seen=now,
                    )
                    session.add(new_item)
                    session.flush()  # populate new_item.id
                    item_id = new_item.id

                # Record changes in history table
                change_events: list[ChangeEvent] = getattr(item, "_change_events", [])
                for ev in change_events:
                    ev_type = getattr(ev, "type", ev.get("type") if isinstance(ev, dict) else None)
                    ev_field = getattr(ev, "field", ev.get("field") if isinstance(ev, dict) else None)
                    ev_old = getattr(ev, "old", ev.get("old") if isinstance(ev, dict) else None)
                    ev_new = getattr(ev, "new", ev.get("new") if isinstance(ev, dict) else None)

                    if ev_type in ("PRICE_DROP", "PRICE_RISE", "UPDATED") and ev_field:
                        history_entry = ItemHistory(
                            item_id=item_id,
                            field=str(ev_field),
                            old_value=str(ev_old) if ev_old is not None else None,
                            new_value=str(ev_new) if ev_new is not None else None,
                            changed_at=now,
                        )
                        session.add(history_entry)

                session.commit()
        except SQLAlchemyError as exc:
            logger.error(
                "sqlite_store_pipeline_error",
                error=str(exc),
                source=item.source,
                external_id=item.external_id,
            )
        return item
