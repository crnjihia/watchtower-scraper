import os
import structlog
import asyncio
from celery import Celery, shared_task
from celery.schedules import crontab
from scrapy.crawler import CrawlerProcess
from . import settings as scraper_settings

log = structlog.get_logger(__name__)

celery_app = Celery(
    "angalia",
    broker=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1"),
)

celery_app.conf.beat_schedule = {
    "run-job-spiders": {
        "task": "angalia.tasks.run_spider",
        "schedule": crontab(minute=0, hour="*/4"),  # every 4 hours
        "args": ("jobs",),
    },
    "run-product-spiders": {
        "task": "angalia.tasks.run_spider",
        "schedule": crontab(minute=0, hour="*/6"),  # every 6 hours
        "args": ("products",),
    },
    "telegram-alerts": {
        "task": "angalia.tasks.telegram_alerts_task",
        "schedule": crontab(minute="*/5"),  # every 5 minutes
    },
    "daily-email-digest": {
        "task": "angalia.tasks.email_digest_task",
        "schedule": crontab(minute=0, hour=5),  # 05:00 UTC == 08:00 EAT
    },
    "cleanup-old-items": {
        "task": "angalia.tasks.cleanup_old_items",
        "schedule": crontab(minute=0, hour=0, day_of_week="sun"),
    },
}
celery_app.conf.timezone = "UTC"


def _run_crawler(spider_names):
    process = CrawlerProcess(settings=scraper_settings)
    for name in spider_names:
        process.crawl(name)
    process.start()  # blocking until all crawlers finish


@shared_task(name="angalia.tasks.run_spider")
def run_spider(spider_group: str):
    log.info("run_spider_start", group=spider_group)
    if spider_group == "jobs":
        spider_names = ["brighter_monday", "fuzu", "myjobmag"]
    elif spider_group == "products":
        spider_names = ["jumia", "kilimall"]
    else:
        log.error("unknown_spider_group", group=spider_group)
        return
    _run_crawler(spider_names)
    log.info("run_spider_finished", group=spider_group)

# Import notifier functions with distinct names to avoid collision with task names
from .notify.telegram import send_telegram_alerts as telegram_send_alerts
from .notify.email import send_email_digest as email_send_digest


@shared_task(name="angalia.tasks.telegram_alerts_task")
def telegram_alerts_task():
    """Pull recent change events from the DB (placeholder) and forward them to Telegram."""
    recent_events = []  # TODO: replace with real query
    if recent_events:
        asyncio.run(telegram_send_alerts(recent_events))
    else:
        log.info("no_telegram_events")


@shared_task(name="angalia.tasks.email_digest_task")
def email_digest_task():
    """Gather all change events from the last 24 h and send a daily digest via SendGrid."""
    events = []  # TODO: replace with real query
    if events:
        email_send_digest(events)
    else:
        log.info("no_email_events")


@shared_task(name="angalia.tasks.cleanup_old_items")
def cleanup_old_items():
    """Archive items that have not been seen in the last 30 days."""
    from .storage.db import get_session
    from .storage.models import Item
    from datetime import datetime, timedelta

    cutoff = datetime.utcnow() - timedelta(days=30)
    with get_session() as session:
        old_items = session.query(Item).filter(Item.last_seen < cutoff).all()
        for itm in old_items:
            session.delete(itm)
        session.commit()
    log.info("cleanup_done", removed=len(old_items))
