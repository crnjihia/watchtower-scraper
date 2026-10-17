"""Seed demo database with sample items and change events for reviewer testing."""

import argparse
from datetime import UTC, datetime, timedelta

from watchtower.db.models import ChangeKind
from watchtower.db.repository import (
    create_change_event,
    create_snapshot,
    create_spider_run,
    finish_spider_run,
    upsert_item,
)
from watchtower.db.session import get_session_factory, init_db
from watchtower.logging import get_logger, setup_logging
from watchtower.notifiers.dispatcher import NotificationDispatcher

logger = get_logger(__name__)


def seed_demo_data(dispatch_alerts: bool = False) -> None:
    """Populate database with sample job and e-commerce listings exhibiting changes."""
    setup_logging()
    init_db()
    session = get_session_factory()()

    now = datetime.now(UTC).replace(tzinfo=None)
    yesterday = now - timedelta(days=1)

    print("[*] Seeding Watchtower Scraper demonstration data...")

    # 1. New Job Listing on BrighterMonday
    item1, _ = upsert_item(
        session=session,
        site="brighter_monday",
        external_id="bm-lead-py-ai-901",
        url="https://www.brightermonday.co.ke/jobs/lead-python-ai-engineer-901",
        title="Lead Python & AI Engineer",
        company="Safaricom PLC",
        location="Nairobi, Kenya",
        category="Software Engineering",
        scraped_at=now,
    )
    create_snapshot(session, item_id=item1.id, price_kes=None, scraped_at=now)
    ev1 = create_change_event(
        session=session,
        item_id=item1.id,
        kind=ChangeKind.NEW_LISTING,
        diff={"salary_kes": "350,000 - 500,000", "type": "new_listing"},
        created_at=now,
    )

    # 2. New Job Listing on Fuzu
    item2, _ = upsert_item(
        session=session,
        site="fuzu",
        external_id="fz-cloud-arch-902",
        url="https://www.fuzu.com/jobs/senior-cloud-solutions-architect-902",
        title="Senior Cloud Solutions Architect",
        company="Equity Group",
        location="Nairobi, Kenya",
        category="Cloud & Infrastructure",
        scraped_at=now,
    )
    create_snapshot(session, item_id=item2.id, price_kes=None, scraped_at=now)
    ev2 = create_change_event(
        session=session,
        item_id=item2.id,
        kind=ChangeKind.NEW_LISTING,
        diff={"type": "new_listing"},
        created_at=now,
    )

    # 3. Price Drop on Jumia Product
    item3, _ = upsert_item(
        session=session,
        site="jumia",
        external_id="jumia-iphone-15-pro-max-903",
        url="https://www.jumia.co.ke/p/apple-iphone-15-pro-max-256gb-903.html",
        title="Apple iPhone 15 Pro Max 256GB - Titanium Natural",
        company="Official Apple Store",
        location="Kenya",
        category="Smartphones",
        scraped_at=now,
    )
    # Historic baseline snapshot yesterday
    create_snapshot(session, item_id=item3.id, price_kes=185000.0, scraped_at=yesterday)
    # Current snapshot today
    create_snapshot(session, item_id=item3.id, price_kes=169999.0, scraped_at=now)
    ev3 = create_change_event(
        session=session,
        item_id=item3.id,
        kind=ChangeKind.PRICE_DROP,
        diff={"old": 185000.0, "new": 169999.0, "pct": 8.11},
        created_at=now,
    )

    # 4. Price Increase on Kilimall Product
    item4, _ = upsert_item(
        session=session,
        site="kilimall",
        external_id="kili-sony-headphones-904",
        url="https://www.kilimall.co.ke/item/sony-wh1000xm5-headphones-904",
        title="Sony WH-1000XM5 Wireless Noise Canceling Headphones",
        company="Sony Kenya Official",
        location="Kenya",
        category="Audio",
        scraped_at=now,
    )
    create_snapshot(session, item_id=item4.id, price_kes=42000.0, scraped_at=yesterday)
    create_snapshot(session, item_id=item4.id, price_kes=48500.0, scraped_at=now)
    ev4 = create_change_event(
        session=session,
        item_id=item4.id,
        kind=ChangeKind.PRICE_INCREASE,
        diff={"old": 42000.0, "new": 48500.0, "pct": 15.48},
        created_at=now,
    )

    # 5. Removed Job Listing on MyJobMag
    item5, _ = upsert_item(
        session=session,
        site="my_job_mag",
        external_id="mjm-security-analyst-905",
        url="https://www.myjobmag.co.ke/jobs/cyber-security-analyst-905",
        title="Cyber Security Operations Analyst",
        company="M-KOPA Kenya",
        location="Nairobi",
        category="Cybersecurity",
        scraped_at=now - timedelta(hours=36),
    )
    item5.active = False
    ev5 = create_change_event(
        session=session,
        item_id=item5.id,
        kind=ChangeKind.REMOVED,
        diff={"reason": "Not seen for 36 hours (closed)"},
        created_at=now,
    )

    # 6. Audit Spider Run
    run = create_spider_run(session, spider="demo_seeder")
    finish_spider_run(session, run_id=run.id, items_seen=5, errors=0, status="completed")

    session.commit()
    print("[+] Seeded 5 items, 5 snapshots, 5 change events, and 1 spider run.")

    events = [ev1, ev2, ev3, ev4, ev5]

    if dispatch_alerts:
        print("\n[*] Dispatching alerts across configured channels (Telegram / Email)...")
        dispatcher = NotificationDispatcher()
        stats = dispatcher.dispatch_events(events, session)
        print(f"[+] Dispatch complete: {stats}")
    else:
        print(
            "\n[i] Alerts were seeded as 'unnotified' in the database.\n"
            "To send them via Telegram/Email now, run:\n"
            "   python scripts/seed_demo.py --notify\n"
            "Or let the Celery worker handle them via:\n"
            "   celery -A watchtower.tasks.celery_app call watchtower.tasks.notify.send_alert\n"
        )

    session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed demo items and events for Watchtower Scraper.")
    parser.add_argument(
        "--notify",
        action="store_true",
        help="Immediately trigger notification dispatch to configured channels",
    )
    args = parser.parse_args()
    seed_demo_data(dispatch_alerts=args.notify)
