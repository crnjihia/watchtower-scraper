"""Unit tests for Celery tasks: notify and maintenance."""

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from watchtower.db.models import Base, ChangeEvent, ChangeKind, Item, ItemSnapshot, SpiderRun
from watchtower.tasks.maintenance import (
    mark_missing_items,
    prune_snapshots,
    system_health_report,
)
from watchtower.tasks.notify import send_alert


@pytest.fixture
def tasks_db_session(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> Any:
    engine = create_engine(f"sqlite:///{tmp_path}/test_tasks.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)

    monkeypatch.setattr("watchtower.tasks.maintenance.get_session_factory", lambda: factory)
    monkeypatch.setattr("watchtower.tasks.notify.get_session_factory", lambda: factory)
    yield factory
    engine.dispose()


def test_maintenance_prune_and_health_report(tasks_db_session: Any) -> None:
    session = tasks_db_session()
    now = datetime.now(UTC).replace(tzinfo=None)

    item = Item(site="jumia", external_id="maint-1", url="https://jumia.co.ke/1", title="Maint Item")
    session.add(item)
    session.commit()

    # 1 snapshot 100 days old, 1 snapshot today
    old_snap = ItemSnapshot(item_id=item.id, price_kes=100.0, scraped_at=now - timedelta(days=100))
    new_snap = ItemSnapshot(item_id=item.id, price_kes=95.0, scraped_at=now)
    run = SpiderRun(spider="jumia", status="completed")
    session.add_all([old_snap, new_snap, run])
    session.commit()
    session.close()

    # Test prune snapshots > 90 days
    result = prune_snapshots(retention_days=90)
    assert result["deleted_snapshots"] == 1

    # Test health report
    report = system_health_report()
    assert report["total_items"] == 1
    assert report["snapshots_stored"] == 1
    assert report["total_spider_runs"] == 1


def test_maintenance_mark_missing_items(tasks_db_session: Any) -> None:
    session = tasks_db_session()
    old_time = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=48)
    item = Item(
        site="fuzu",
        external_id="fz-missing",
        url="https://fuzu.com/1",
        title="Old Job",
        last_seen_at=old_time,
        active=True,
    )
    session.add(item)
    session.commit()
    session.close()

    res = mark_missing_items(missing_after_hours=24)
    assert res["marked_inactive"] == 1


def test_send_alert_task_empty_and_with_events(tasks_db_session: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    # 1. Empty test
    res = send_alert()
    assert res["status"] == "no_events_to_notify"

    # 2. Add an unnotified event
    session = tasks_db_session()
    item = Item(site="jumia", external_id="alert-item", url="https://jumia.co.ke/a", title="Alert Phone")
    session.add(item)
    session.commit()

    ev = ChangeEvent(item_id=item.id, kind=ChangeKind.PRICE_DROP, diff={"old": 100, "new": 90, "pct": 10})
    session.add(ev)
    session.commit()
    ev_id = ev.id
    session.close()

    mock_dispatcher = MagicMock()
    mock_dispatcher.dispatch_events.return_value = {"total": 1, "notified": 1}
    monkeypatch.setattr("watchtower.tasks.notify.NotificationDispatcher", lambda: mock_dispatcher)

    res2 = send_alert(change_event_id=ev_id)
    assert res2["status"] == "dispatched"
    assert mock_dispatcher.dispatch_events.called
