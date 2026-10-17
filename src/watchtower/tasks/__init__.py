"""Celery tasks and background scheduling module."""

from watchtower.tasks.celery_app import celery_app
from watchtower.tasks.crawl import run_spider
from watchtower.tasks.maintenance import prune_snapshots, system_health_report
from watchtower.tasks.notify import send_alert

__all__ = [
    "celery_app",
    "run_spider",
    "send_alert",
    "prune_snapshots",
    "system_health_report",
]
