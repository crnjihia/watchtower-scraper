import asyncio
import json
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from celery import shared_task

from .notify.email import send_email_digest as notify_email
from .notify.telegram import send_telegram_alerts as notify_telegram
from .storage.db import get_session, init_db
from .storage.models import Item, ItemHistory

logger = structlog.get_logger(__name__)


def get_recent_change_events(since_hours: int = 24) -> list[dict[str, Any]]:
    """
    Collect new listings and historical changes from SQLite.
    Returns structured list of event dictionaries for notifiers.
    """
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=since_hours)
    events: list[dict[str, Any]] = []

    try:
        with get_session() as session:
            # 1. New items first seen within the window
            new_items = (
                session.query(Item)
                .filter(Item.first_seen >= cutoff)
                .order_by(Item.first_seen.desc())
                .all()
            )
            for itm in new_items:
                data = itm.data if isinstance(itm.data, dict) else json.loads(itm.data)
                events.append(
                    {
                        "type": "NEW",
                        "source": itm.source,
                        "external_id": itm.external_id,
                        "field": None,
                        "old": None,
                        "new": data,
                        "url": itm.url,
                    }
                )

            # 2. History changes (price drops/rises and updates)
            history_rows = (
                session.query(ItemHistory, Item)
                .join(Item, Item.id == ItemHistory.item_id)
                .filter(ItemHistory.changed_at >= cutoff)
                .order_by(ItemHistory.changed_at.desc())
                .all()
            )
            for hist, itm in history_rows:
                ev_type = "UPDATED"
                if hist.field == "price":
                    try:
                        old_p = float(hist.old_value) if hist.old_value else 0.0
                        new_p = float(hist.new_value) if hist.new_value else 0.0
                        ev_type = "PRICE_DROP" if new_p < old_p else "PRICE_RISE"
                    except (ValueError, TypeError):
                        ev_type = "UPDATED"

                data = itm.data if isinstance(itm.data, dict) else json.loads(itm.data)
                events.append(
                    {
                        "type": ev_type,
                        "source": itm.source,
                        "external_id": itm.external_id,
                        "field": hist.field,
                        "old": hist.old_value,
                        "new": hist.new_value,
                        "url": itm.url,
                        "title": data.get("title") or data.get("name"),
                    }
                )
    except Exception as exc:
        logger.error("get_recent_change_events_error", error=str(exc))

    return events


def _run_crawler(spider_names: list[str]):
    """Execute Scrapy CrawlerProcess with the given spider names."""
    from scrapy.crawler import CrawlerProcess
    from scrapy.utils.project import get_project_settings

    init_db()
    settings = get_project_settings()
    process = CrawlerProcess(settings)
    for name in spider_names:
        logger.info("queuing_spider", spider=name)
        process.crawl(name)
    process.start()


@shared_task(name="angalia.tasks.run_spider")
def run_spider(spider_name: str):
    """
    Run Scrapy spiders by specific spider name or group:
    - 'jobs': ['brighter_monday', 'fuzu', 'myjobmag']
    - 'products': ['jumia', 'kilimall']
    - or individual spider name
    """
    logger.info("run_spider_task_start", target=spider_name)

    if spider_name == "jobs":
        spiders = ["brighter_monday", "fuzu", "myjobmag"]
    elif spider_name == "products":
        spiders = ["jumia", "kilimall"]
    elif spider_name in ["brighter_monday", "fuzu", "myjobmag", "jumia", "kilimall"]:
        spiders = [spider_name]
    else:
        logger.error("unknown_spider_or_group", spider_name=spider_name)
        return

    _run_crawler(spiders)
    logger.info("run_spider_task_completed", spiders=spiders)


@shared_task(name="angalia.tasks.send_telegram_alerts")
def send_telegram_alerts(events: list[dict[str, Any]] | None = None):
    """Drain recent changes from the database and dispatch Telegram alerts."""
    logger.info("send_telegram_alerts_task_start")
    if events is None:
        events = get_recent_change_events(since_hours=6)

    if not events:
        logger.info("no_pending_telegram_alerts")
        return 0

    sent_count = asyncio.run(notify_telegram(events, check_dedup=True))
    logger.info("send_telegram_alerts_task_done", sent=sent_count)
    return sent_count


@shared_task(name="angalia.tasks.send_email_digest")
def send_email_digest(events: list[dict[str, Any]] | None = None):
    """Collect 24-hour change digest and dispatch via SendGrid."""
    logger.info("send_email_digest_task_start")
    if events is None:
        events = get_recent_change_events(since_hours=24)

    if not events:
        logger.info("no_events_for_daily_digest")
        return None

    result = notify_email(events, check_dedup=True)
    logger.info("send_email_digest_task_done", total_events=len(events))
    return result


@shared_task(name="angalia.tasks.cleanup_old_items")
def cleanup_old_items(retention_days: int = 30):
    """Archive / delete items not seen in the last 30 days."""
    logger.info("cleanup_old_items_task_start", retention_days=retention_days)
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=retention_days)
    deleted_count = 0

    try:
        with get_session() as session:
            old_items = session.query(Item).filter(Item.last_seen < cutoff).all()
            deleted_count = len(old_items)
            for itm in old_items:
                session.delete(itm)
            session.commit()
        logger.info("cleanup_old_items_task_done", deleted=deleted_count)
    except Exception as exc:
        logger.error("cleanup_old_items_error", error=str(exc))

    return deleted_count
