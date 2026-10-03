import os

from celery import Celery
from celery.schedules import crontab

BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")

celery_app = Celery("angalia", broker=BROKER_URL, backend=RESULT_BACKEND)

celery_app.conf.update(
    timezone="UTC",
    enable_utc=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    beat_schedule={
        "jobs-scraper-every-4h": {
            "task": "angalia.tasks.run_spider",
            "schedule": crontab(minute=0, hour="*/4"),
            "args": ("jobs",),
        },
        "products-scraper-every-6h": {
            "task": "angalia.tasks.run_spider",
            "schedule": crontab(minute=0, hour="*/6"),
            "args": ("products",),
        },
        "telegram-alerts-every-5m": {
            "task": "angalia.tasks.send_telegram_alerts",
            "schedule": crontab(minute="*/5"),
        },
        "email-digest-daily-08eat": {
            "task": "angalia.tasks.send_email_digest",
            "schedule": crontab(minute=0, hour=5),  # 05:00 UTC == 08:00 EAT
        },
        "cleanup-weekly-sunday": {
            "task": "angalia.tasks.cleanup_old_items",
            "schedule": crontab(minute=0, hour=0, day_of_week="sun"),
        },
    },
)

celery_app.autodiscover_tasks(["angalia"])

__all__ = ["celery_app"]
