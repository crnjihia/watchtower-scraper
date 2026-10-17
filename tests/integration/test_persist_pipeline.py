"""Integration tests for PersistPipeline using in-memory SQLite."""

from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from watchtower.db.models import Base, ChangeEvent, ChangeKind, Item, ItemSnapshot
from watchtower.pipelines.persist import PersistPipeline


@pytest.fixture
def test_db_session(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Fixture providing isolated in-memory SQLite database."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    monkeypatch.setattr("watchtower.pipelines.persist.get_session_factory", lambda: factory)
    yield factory
    engine.dispose()


def test_persist_pipeline_idempotency_and_price_changes(test_db_session: Any) -> None:
    pipeline = PersistPipeline()

    item_crawl_1 = {
        "site": "jumia",
        "external_id": "iphone-15",
        "url": "https://jumia.co.ke/p/iphone-15",
        "title": "Apple iPhone 15",
        "company": "Official Apple",
        "price_kes": 150000.0,
        "currency": "KES",
        "location": "Nairobi",
        "category": "Smartphones",
    }

    # 1. First crawl: new item created with snapshot and new_listing event
    pipeline.process_item(dict(item_crawl_1), spider=None)

    session: Session = test_db_session()
    items = session.query(Item).all()
    assert len(items) == 1
    assert items[0].title == "Apple iPhone 15"

    snapshots = session.query(ItemSnapshot).all()
    assert len(snapshots) == 1
    assert snapshots[0].price_kes == 150000.0

    events = session.query(ChangeEvent).all()
    assert len(events) == 1
    assert events[0].kind == ChangeKind.NEW_LISTING
    session.close()

    # 2. Idempotency test: re-running crawl with identical data must NOT duplicate ChangeEvents!
    pipeline.process_item(dict(item_crawl_1), spider=None)

    session = test_db_session()
    assert session.query(Item).count() == 1
    assert session.query(ItemSnapshot).count() == 1
    assert session.query(ChangeEvent).count() == 1  # No duplicate event!
    session.close()

    # 3. Third crawl: price drop by 10% (150,000 -> 135,000)
    item_crawl_2 = dict(item_crawl_1)
    item_crawl_2["price_kes"] = 135000.0

    pipeline.process_item(item_crawl_2, spider=None)

    session = test_db_session()
    assert session.query(Item).count() == 1
    assert session.query(ItemSnapshot).count() == 2

    events = session.query(ChangeEvent).order_by(ChangeEvent.id.asc()).all()
    assert len(events) == 2
    assert events[1].kind == ChangeKind.PRICE_DROP
    assert events[1].diff["old"] == 150000.0
    assert events[1].diff["new"] == 135000.0
    assert events[1].diff["pct"] == 10.0
    session.close()

    # 4. Fourth crawl: price fluctuation under threshold (0.1% change) -> no new ChangeEvent
    item_crawl_3 = dict(item_crawl_2)
    item_crawl_3["price_kes"] = 135050.0  # +0.037% change (< 1.0%)

    pipeline.process_item(item_crawl_3, spider=None)

    session = test_db_session()
    assert session.query(ChangeEvent).count() == 2  # Still 2 events!
    session.close()
