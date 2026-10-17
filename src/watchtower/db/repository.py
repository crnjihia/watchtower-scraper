"""Database repository helpers for items, snapshots, events, and runs."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import delete, desc, select, update
from sqlalchemy.orm import Session

from watchtower.db.models import ChangeEvent, ChangeKind, Item, ItemSnapshot, SpiderRun, utc_now


def get_item(session: Session, site: str, external_id: str) -> Optional[Item]:
    """Retrieve an item by site and external_id."""
    stmt = select(Item).where(Item.site == site, Item.external_id == external_id)
    return session.execute(stmt).scalar_one_or_none()


def upsert_item(
    session: Session,
    site: str,
    external_id: str,
    url: str,
    title: str,
    company: Optional[str] = None,
    location: Optional[str] = None,
    category: Optional[str] = None,
    scraped_at: Optional[datetime] = None,
) -> tuple[Item, bool]:
    """Upsert an item record. Returns tuple of (Item, is_new)."""
    now = scraped_at or utc_now()
    item = get_item(session, site, external_id)
    is_new = False

    if item is None:
        is_new = True
        item = Item(
            site=site,
            external_id=external_id,
            url=url,
            title=title,
            company=company,
            location=location,
            category=category,
            first_seen_at=now,
            last_seen_at=now,
            active=True,
        )
        session.add(item)
        session.flush()
    else:
        item.url = url
        item.title = title
        if company is not None:
            item.company = company
        if location is not None:
            item.location = location
        if category is not None:
            item.category = category
        item.last_seen_at = now
        item.active = True
        session.flush()

    return item, is_new


def create_snapshot(
    session: Session,
    item_id: int,
    price_kes: Optional[float],
    scraped_at: Optional[datetime] = None,
) -> ItemSnapshot:
    """Record a price snapshot for an item."""
    snapshot = ItemSnapshot(
        item_id=item_id,
        price_kes=price_kes,
        scraped_at=scraped_at or utc_now(),
    )
    session.add(snapshot)
    session.flush()
    return snapshot


def get_latest_snapshot(session: Session, item_id: int) -> Optional[ItemSnapshot]:
    """Get the most recent snapshot for an item."""
    stmt = (
        select(ItemSnapshot)
        .where(ItemSnapshot.item_id == item_id)
        .order_by(desc(ItemSnapshot.scraped_at), desc(ItemSnapshot.id))
        .limit(1)
    )
    return session.execute(stmt).scalar_one_or_none()


def create_change_event(
    session: Session,
    item_id: int,
    kind: ChangeKind,
    diff: Optional[Dict[str, Any]] = None,
    created_at: Optional[datetime] = None,
) -> ChangeEvent:
    """Create a change event."""
    event = ChangeEvent(
        item_id=item_id,
        kind=kind,
        diff=diff or {},
        created_at=created_at or utc_now(),
    )
    session.add(event)
    session.flush()
    return event


def get_unnotified_events(session: Session, limit: int = 100) -> Sequence[ChangeEvent]:
    """Fetch unnotified change events with associated item details."""
    stmt = (
        select(ChangeEvent)
        .join(ChangeEvent.item)
        .where(ChangeEvent.notified_at.is_(None))
        .order_by(ChangeEvent.created_at.asc())
        .limit(limit)
    )
    return session.execute(stmt).scalars().all()


def mark_event_notified(session: Session, event_id: int, notified_at: Optional[datetime] = None) -> None:
    """Mark a change event as notified."""
    now = notified_at or utc_now()
    session.execute(
        update(ChangeEvent)
        .where(ChangeEvent.id == event_id)
        .values(notified_at=now)
    )
    session.flush()


def mark_missing_items_inactive(
    session: Session,
    site: Optional[str] = None,
    missing_after_hours: int = 24,
) -> List[ChangeEvent]:
    """Mark items not seen within threshold as inactive and emit 'removed' ChangeEvents."""
    cutoff = utc_now() - timedelta(hours=missing_after_hours)
    query = select(Item).where(Item.active.is_(True), Item.last_seen_at < cutoff)
    if site:
        query = query.where(Item.site == site)

    missing_items = session.execute(query).scalars().all()
    events = []

    for item in missing_items:
        item.active = False
        event = create_change_event(
            session=session,
            item_id=item.id,
            kind=ChangeKind.REMOVED,
            diff={"reason": f"Not seen for {missing_after_hours} hours", "last_seen_at": item.last_seen_at.isoformat()},
        )
        events.append(event)

    session.flush()
    return events


def create_spider_run(session: Session, spider: str) -> SpiderRun:
    """Initialize a new spider execution run."""
    run = SpiderRun(
        spider=spider,
        started_at=utc_now(),
        items_seen=0,
        errors=0,
        status="running",
    )
    session.add(run)
    session.flush()
    return run


def finish_spider_run(
    session: Session,
    run_id: int,
    items_seen: int,
    errors: int,
    status: str = "completed",
) -> Optional[SpiderRun]:
    """Finish a spider execution record."""
    run = session.get(SpiderRun, run_id)
    if run:
        run.finished_at = utc_now()
        run.items_seen = items_seen
        run.errors = errors
        run.status = status
        session.flush()
    return run


def prune_old_snapshots(session: Session, retention_days: int = 90) -> int:
    """Delete snapshots older than retention_days."""
    cutoff = utc_now() - timedelta(days=retention_days)
    stmt = delete(ItemSnapshot).where(ItemSnapshot.scraped_at < cutoff)
    result = session.execute(stmt)
    session.flush()
    return result.rowcount or 0


def get_recent_runs(session: Session, limit: int = 50) -> Sequence[SpiderRun]:
    """Get the most recent spider runs."""
    stmt = select(SpiderRun).order_by(desc(SpiderRun.started_at)).limit(limit)
    return session.execute(stmt).scalars().all()


def get_recent_changes(session: Session, limit: int = 50) -> Sequence[ChangeEvent]:
    """Get recent change events with items loaded."""
    stmt = select(ChangeEvent).join(ChangeEvent.item).order_by(desc(ChangeEvent.created_at)).limit(limit)
    return session.execute(stmt).scalars().all()
