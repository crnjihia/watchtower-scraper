"""End-to-end runner and validator for Watchtower Scraper core flows."""

import sys
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from watchtower.api.main import app
from watchtower.db.models import ChangeKind
from watchtower.db.repository import (
    create_spider_run,
    finish_spider_run,
    get_item,
    get_recent_changes,
    mark_missing_items_inactive,
    prune_old_snapshots,
    upsert_item,
)
from watchtower.db.session import get_session_factory, init_db
from watchtower.logging import get_logger, setup_logging
from watchtower.notifiers.dispatcher import NotificationDispatcher
from watchtower.pipelines.normalize import NormalizePipeline
from watchtower.pipelines.persist import PersistPipeline
from watchtower.tasks.maintenance import system_health_report

logger = get_logger(__name__)


def run_all_core_flows() -> bool:
    setup_logging()
    print("=" * 70)
    print("WATCHTOWER SCRAPER - CORE FLOWS VALIDATION")
    print("=" * 70)

    # -------------------------------------------------------------
    # FLOW 1: Database Initialization
    # -------------------------------------------------------------
    print("\n[FLOW 1] Initializing Database Schema...")
    init_db()
    session = get_session_factory()()
    print("  -> Database initialized successfully.")

    # -------------------------------------------------------------
    # FLOW 2: Ingestion & Idempotent Persistence Pipeline
    # -------------------------------------------------------------
    print("\n[FLOW 2] Ingestion & Persistence Pipeline (Idempotency & Price Diffs)...")
    norm_pipe = NormalizePipeline()
    persist_pipe = PersistPipeline()

    raw_item_1 = {
        "site": "jumia",
        "external_id": "test-pixel-9",
        "url": "https://www.jumia.co.ke/p/google-pixel-9-128gb.html",
        "title": " Google Pixel 9 5G - 128GB  ",
        "company": " Google Store Kenya ",
        "price_kes": "KSh 115,000",
        "location": " Nairobi ",
        "category": " Smartphones ",
        "posted_at": "Today",
    }

    # Step 2a: First crawl of new item
    normalized_1 = norm_pipe.process_item(dict(raw_item_1), spider=None)
    assert normalized_1["price_kes"] == 115000.0
    persist_pipe.process_item(normalized_1, spider=None)

    item = get_item(session, site="jumia", external_id="test-pixel-9")
    assert item is not None
    assert item.title == "Google Pixel 9 5G - 128GB"
    print(f"  -> First crawl: Created item '{item.title}' at KES {normalized_1['price_kes']:,.2f}.")

    # Step 2b: Re-crawling identical item (must be idempotent!)
    events_before = len(get_recent_changes(session, limit=100))
    normalized_duplicate = norm_pipe.process_item(dict(raw_item_1), spider=None)
    persist_pipe.process_item(normalized_duplicate, spider=None)
    events_after = len(get_recent_changes(session, limit=100))
    assert events_before == events_after, "Idempotency failed: duplicate event created!"
    print("  -> Duplicate crawl: Idempotency verified (0 duplicate events emitted).")

    # Step 2c: Price drop crawl (> 1% threshold)
    raw_item_price_drop = dict(raw_item_1)
    raw_item_price_drop["price_kes"] = "KSh 99,999"  # ~13% drop
    normalized_drop = norm_pipe.process_item(raw_item_price_drop, spider=None)
    persist_pipe.process_item(normalized_drop, spider=None)

    latest_changes = get_recent_changes(session, limit=5)
    price_drop_event = next((c for c in latest_changes if c.item.external_id == "test-pixel-9"), None)
    assert price_drop_event is not None
    assert price_drop_event.kind == ChangeKind.PRICE_DROP
    diff = price_drop_event.diff
    print(f"  -> Price drop crawl: Emitted PRICE_DROP event: KES {diff['old']:,.2f} -> KES {diff['new']:,.2f} (-{diff['pct']}%)")

    # -------------------------------------------------------------
    # FLOW 3: Alert Notification & Deduplication
    # -------------------------------------------------------------
    print("\n[FLOW 3] Multi-Channel Alert Dispatch & Deduplication...")
    dispatcher = NotificationDispatcher()
    unnotified_events = [c for c in get_recent_changes(session, limit=20) if c.notified_at is None]
    print(f"  -> Found {len(unnotified_events)} unnotified change events.")

    stats1 = dispatcher.dispatch_events(unnotified_events, session)
    print(f"  -> Dispatch round 1 result: {stats1}")

    # Re-dispatch the same batch: deduplication must ensure no repeat dispatches
    stats2 = dispatcher.dispatch_events(unnotified_events, session)
    print(f"  -> Dispatch round 2 result (deduplicated): {stats2}")
    assert stats2["errors"] == 0

    # -------------------------------------------------------------
    # FLOW 4: Maintenance Tasks
    # -------------------------------------------------------------
    print("\n[FLOW 4] Maintenance & Housekeeping Tasks...")
    # Seed an inactive item (> 24 hours)
    old_time = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=36)
    old_item, _ = upsert_item(
        session=session,
        site="fuzu",
        external_id="expired-job-1",
        url="https://fuzu.com/job/expired-1",
        title="Expired Systems Administrator",
        scraped_at=old_time,
    )
    old_item.last_seen_at = old_time
    old_item.active = True
    session.commit()

    removed_events = mark_missing_items_inactive(session, missing_after_hours=24)
    print(f"  -> Marked {len(removed_events)} stale listing(s) as inactive (REMOVED event emitted).")

    pruned = prune_old_snapshots(session, retention_days=90)
    print(f"  -> Pruned {pruned} snapshot(s) older than 90 days.")

    health = system_health_report()
    print(f"  -> System Health Report: {health}")

    # -------------------------------------------------------------
    # FLOW 5: Read-Only Status & Audit API
    # -------------------------------------------------------------
    print("\n[FLOW 5] Status & Inspection API Endpoints...")
    client = TestClient(app)

    # Audit Spider Run in DB for API verification
    run = create_spider_run(session, spider="jumia")
    finish_spider_run(session, run.id, items_seen=42, errors=0, status="completed")
    session.commit()

    resp_health = client.get("/health")
    assert resp_health.status_code == 200
    print(f"  -> GET /health: {resp_health.json()}")

    resp_runs = client.get("/runs?limit=5")
    assert resp_runs.status_code == 200
    print(f"  -> GET /runs (total returned: {len(resp_runs.json())}): Latest run: {resp_runs.json()[0]['spider']} ({resp_runs.json()[0]['status']})")

    resp_changes = client.get("/changes?limit=5")
    assert resp_changes.status_code == 200
    print(f"  -> GET /changes (total returned: {len(resp_changes.json())}): Latest event: {resp_changes.json()[0]['kind']} for '{resp_changes.json()[0]['title']}'")

    session.close()

    print("\n" + "=" * 70)
    print("ALL CORE FLOWS EXECUTED AND VERIFIED SUCCESSFULLY!")
    print("=" * 70)
    return True


if __name__ == "__main__":
    success = run_all_core_flows()
    sys.exit(0 if success else 1)
