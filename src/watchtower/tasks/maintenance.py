"""Maintenance and database housekeeping tasks."""

from typing import Any, Dict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from watchtower.db.models import ChangeEvent, Item, ItemSnapshot, SpiderRun
from watchtower.db.repository import mark_missing_items_inactive, prune_old_snapshots
from watchtower.db.session import get_session_factory
from watchtower.logging import get_logger
from watchtower.tasks.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="watchtower.tasks.maintenance.prune_snapshots")
def prune_snapshots(retention_days: int = 90) -> Dict[str, Any]:
    """Delete historical price snapshots older than retention threshold."""
    session_factory = get_session_factory()
    session: Session = session_factory()
    try:
        deleted = prune_old_snapshots(session, retention_days=retention_days)
        session.commit()
        logger.info("snapshots_pruned", deleted_count=deleted, retention_days=retention_days)
        return {"deleted_snapshots": deleted}
    except Exception as e:
        session.rollback()
        logger.exception("prune_snapshots_failed", error=str(e))
        raise e
    finally:
        session.close()


@celery_app.task(name="watchtower.tasks.maintenance.mark_missing_items")
def mark_missing_items(missing_after_hours: int = 24) -> Dict[str, Any]:
    """Identify items not scraped recently and mark them inactive with a 'removed' event."""
    session_factory = get_session_factory()
    session: Session = session_factory()
    try:
        events = mark_missing_items_inactive(session, missing_after_hours=missing_after_hours)
        session.commit()
        logger.info("missing_items_processed", inactive_count=len(events))
        return {"marked_inactive": len(events)}
    except Exception as e:
        session.rollback()
        logger.exception("mark_missing_items_failed", error=str(e))
        raise e
    finally:
        session.close()


@celery_app.task(name="watchtower.tasks.maintenance.system_health_report")
def system_health_report() -> Dict[str, Any]:
    """Gather high-level statistics on crawler operations and database sizes."""
    session_factory = get_session_factory()
    session: Session = session_factory()
    try:
        items_total = session.execute(select(func.count(Item.id))).scalar() or 0
        items_active = session.execute(select(func.count(Item.id)).where(Item.active.is_(True))).scalar() or 0
        snapshots_count = session.execute(select(func.count(ItemSnapshot.id))).scalar() or 0
        events_unnotified = session.execute(select(func.count(ChangeEvent.id)).where(ChangeEvent.notified_at.is_(None))).scalar() or 0
        runs_count = session.execute(select(func.count(SpiderRun.id))).scalar() or 0

        report = {
            "total_items": items_total,
            "active_items": items_active,
            "snapshots_stored": snapshots_count,
            "pending_alerts": events_unnotified,
            "total_spider_runs": runs_count,
        }
        logger.info("system_health_summary", **report)
        return report
    finally:
        session.close()
