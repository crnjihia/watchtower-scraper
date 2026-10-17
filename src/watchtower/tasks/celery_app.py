"""Celery application configuration with Celery Beat schedule."""

from celery import Celery
from celery.schedules import crontab

from watchtower.config import get_settings

settings = get_settings()

celery_app = Celery(
    "watchtower",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "watchtower.tasks.crawl",
        "watchtower.tasks.notify",
        "watchtower.tasks.maintenance",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Africa/Nairobi",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Celery Beat schedule for automatic execution
celery_app.conf.beat_schedule = {
    # Job Boards: Every 15 minutes during 06:00 - 22:00 EAT
    "crawl-brighter-monday-daytime": {
        "task": "watchtower.tasks.crawl.run_spider",
        "schedule": crontab(minute="*/15", hour="6-22"),
        "args": ["brighter_monday"],
    },
    "crawl-fuzu-daytime": {
        "task": "watchtower.tasks.crawl.run_spider",
        "schedule": crontab(minute="*/15", hour="6-22"),
        "args": ["fuzu"],
    },
    "crawl-my-job-mag-daytime": {
        "task": "watchtower.tasks.crawl.run_spider",
        "schedule": crontab(minute="*/15", hour="6-22"),
        "args": ["my_job_mag"],
    },
    # E-Commerce Sites: Every 30 minutes
    "crawl-jumia-every-30min": {
        "task": "watchtower.tasks.crawl.run_spider",
        "schedule": crontab(minute="*/30"),
        "args": ["jumia"],
    },
    "crawl-kilimall-every-30min": {
        "task": "watchtower.tasks.crawl.run_spider",
        "schedule": crontab(minute="*/30"),
        "args": ["kilimall"],
    },
    # Periodic alert dispatcher for any pending events
    "dispatch-pending-alerts": {
        "task": "watchtower.tasks.notify.send_alert",
        "schedule": crontab(minute="*/2"),
        "args": [],
    },
    # Weekly maintenance: 03:00 Sunday (EAT)
    "weekly-maintenance": {
        "task": "watchtower.tasks.maintenance.prune_snapshots",
        "schedule": crontab(minute=0, hour=3, day_of_week=0),
        "args": [90],
    },
}
