"""Unit tests for change detection logic across all event types and edge cases."""

from datetime import UTC, datetime, timedelta
from typing import Any

from watchtower.db.models import ChangeKind, Item, ItemSnapshot
from watchtower.db.repository import mark_missing_items_inactive
from watchtower.pipelines.change_detect import detect_item_change


def test_detect_new_listing() -> None:
    # 1. New listing: existing item is None
    change = detect_item_change(
        existing_item=None,
        latest_snapshot=None,
        new_price=150000.0,
    )
    assert change is not None
    kind, diff = change
    assert kind == ChangeKind.NEW_LISTING
    assert diff["price_kes"] == 150000.0


def test_detect_price_drop() -> None:
    # 2. Price drop: 100,000 -> 90,000 (10% drop, > 1% threshold)
    item = Item(id=1, site="jumia", external_id="item-1")
    snapshot = ItemSnapshot(id=1, item_id=1, price_kes=100000.0)

    change = detect_item_change(
        existing_item=item,
        latest_snapshot=snapshot,
        new_price=90000.0,
        min_price_delta_pct=1.0,
    )
    assert change is not None
    kind, diff = change
    assert kind == ChangeKind.PRICE_DROP
    assert diff["old"] == 100000.0
    assert diff["new"] == 90000.0
    assert diff["pct"] == 10.0


def test_detect_price_increase() -> None:
    # 3. Price increase: 10,000 -> 12,000 (20% increase)
    item = Item(id=2, site="kilimall", external_id="item-2")
    snapshot = ItemSnapshot(id=2, item_id=2, price_kes=10000.0)

    change = detect_item_change(
        existing_item=item,
        latest_snapshot=snapshot,
        new_price=12000.0,
        min_price_delta_pct=1.0,
    )
    assert change is not None
    kind, diff = change
    assert kind == ChangeKind.PRICE_INCREASE
    assert diff["old"] == 100000.0 or diff["old"] == 10000.0
    assert diff["new"] == 12000.0
    assert diff["pct"] == 20.0


def test_detect_no_change_below_threshold() -> None:
    # Small fluctuation below threshold (e.g. 0.2% change when threshold is 1.0%)
    item = Item(id=3, site="jumia", external_id="item-3")
    snapshot = ItemSnapshot(id=3, item_id=3, price_kes=10000.0)

    change = detect_item_change(
        existing_item=item,
        latest_snapshot=snapshot,
        new_price=10020.0,  # 0.2% increase
        min_price_delta_pct=1.0,
    )
    assert change is None


def test_detect_no_change_identical_price() -> None:
    item = Item(id=4, site="jumia", external_id="item-4")
    snapshot = ItemSnapshot(id=4, item_id=4, price_kes=50000.0)

    change = detect_item_change(
        existing_item=item,
        latest_snapshot=snapshot,
        new_price=50000.0,
        min_price_delta_pct=1.0,
    )
    assert change is None


def test_detect_removed_event(tmp_path: Any) -> None:
    # 4. Removed event: item unseen for threshold hours
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from watchtower.db.models import Base

    db_path = f"sqlite:///{tmp_path}/test_removed.db"
    engine = create_engine(db_path)
    Base.metadata.create_all(engine)
    session = Session(engine)

    old_date = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=30)
    item = Item(
        site="brighter_monday",
        external_id="job-old-99",
        url="https://brightermonday.co.ke/job/99",
        title="Old Job",
        last_seen_at=old_date,
        active=True,
    )
    session.add(item)
    session.commit()

    try:
        events = mark_missing_items_inactive(session, missing_after_hours=24)
        assert len(events) == 1
        assert events[0].kind == ChangeKind.REMOVED
        assert item.active is False
    finally:
        session.close()
        engine.dispose()
