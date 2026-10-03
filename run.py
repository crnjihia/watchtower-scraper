"""
Angalia Scraper - Unified Application Runner & CLI
Usage:
    python run.py status
    python run.py crawl [spider_name|jobs|products|all] [--limit N]
    python run.py alerts [--channel telegram|email|all] [--hours N] [--dry-run]
    python run.py worker
    python run.py beat
    python run.py test
    python run.py demo
"""

import argparse
import json
import os
import subprocess
import sys

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def cmd_status(args):
    """Show current SQLite database status and item statistics."""
    from angalia.storage.db import get_session, init_db
    from angalia.storage.models import AlertSent, Item, ItemHistory

    init_db()
    print("=" * 60)
    print("  ANGALIA SCRAPER - SYSTEM STATUS")
    print("=" * 60)

    with get_session() as session:
        total_items = session.query(Item).count()
        total_history = session.query(ItemHistory).count()
        total_alerts = session.query(AlertSent).count()

        print(f"Total Stored Items   : {total_items}")
        print(f"Total History Diffs  : {total_history}")
        print(f"Total Alerts Dispatched: {total_alerts}")
        print("-" * 60)

        from sqlalchemy import func

        by_source = (
            session.query(Item.source, func.count(Item.id))
            .group_by(Item.source)
            .all()
        )
        print("Items by Source:")
        if by_source:
            for src, count in by_source:
                print(f"  * {src:<18} : {count:>5} listings")
        else:
            print("  (Database currently has no items)")

        print("-" * 60)
        recent_items = (
            session.query(Item)
            .order_by(Item.last_seen.desc())
            .limit(5)
            .all()
        )
        print("Most Recently Updated Items:")
        if recent_items:
            for itm in recent_items:
                data = itm.data if isinstance(itm.data, dict) else json.loads(itm.data)
                name = data.get("title") or data.get("name") or itm.external_id
                price = data.get("price")
                extra = f" (KES {price:,.2f})" if price is not None else ""
                print(f"  [{itm.source}] {name[:45]}{extra} -> {itm.url}")
        else:
            print("  (None)")
    print("=" * 60)


def cmd_crawl(args):
    """Execute Scrapy crawler for spiders or spider groups."""
    target = args.target.lower()
    spiders = []
    if target == "jobs":
        spiders = ["brighter_monday", "fuzu", "myjobmag"]
    elif target == "products":
        spiders = ["jumia", "kilimall"]
    elif target == "all":
        spiders = ["brighter_monday", "fuzu", "myjobmag", "jumia", "kilimall"]
    else:
        spiders = [target]

    print(f"Starting crawl for: {', '.join(spiders)} (limit={args.limit or 'unlimited'})")

    for sp in spiders:
        cmd = [sys.executable, "-m", "scrapy", "crawl", sp]
        if args.limit:
            cmd.extend(["-s", f"CLOSESPIDER_ITEMCOUNT={args.limit}"])
        print(f"\n--- Running spider: {sp} ---")
        ret = subprocess.run(cmd)
        if ret.returncode != 0:
            print(f"Spider {sp} exited with code {ret.returncode}")


def cmd_alerts(args):
    """Drain events and trigger notifications."""
    from angalia.notify.email import build_subject_and_summary
    from angalia.notify.email import send_email_digest as notify_email
    from angalia.notify.telegram import format_event, send_telegram_alerts
    from angalia.tasks import get_recent_change_events

    hours = args.hours or 24
    print(f"Fetching change events from past {hours} hours...")
    events = get_recent_change_events(since_hours=hours)
    print(f"Discovered {len(events)} change events.")

    if not events:
        print("No pending events to alert.")
        return

    if args.dry_run:
        print("\n[DRY RUN PREVIEW]")
        for i, ev in enumerate(events[:5], 1):
            print(f"{i}. {format_event(ev)}")
        if len(events) > 5:
            print(f"... and {len(events) - 5} more events.")
        subj, summary = build_subject_and_summary(events)
        print(f"\nEmail Digest Subject: {subj}")
        print(f"Email Digest Summary: {summary}")
        return

    channel = args.channel or "all"
    if channel in ("all", "telegram"):
        import asyncio

        print("Dispatching Telegram alerts...")
        sent = asyncio.run(send_telegram_alerts(events, check_dedup=not args.force))
        print(f"Telegram alerts processed: {sent}")

    if channel in ("all", "email"):
        print("Dispatching SendGrid email digest...")
        res = notify_email(events, check_dedup=not args.force)
        if res:
            print("Email digest successfully generated/sent.")
        else:
            print("No email digest sent (events already deduplicated).")


def cmd_worker(args):
    """Run Celery worker process."""
    print("Starting Celery worker (press Ctrl+C to terminate)...")
    cmd = [sys.executable, "-m", "celery", "-A", "angalia.celery_app", "worker", "--loglevel=info", "-P", "solo"]
    subprocess.run(cmd)


def cmd_beat(args):
    """Run Celery beat scheduler."""
    print("Starting Celery beat scheduler (press Ctrl+C to terminate)...")
    cmd = [sys.executable, "-m", "celery", "-A", "angalia.celery_app", "beat", "--loglevel=info"]
    subprocess.run(cmd)


def cmd_test(args):
    """Run test suite with pytest."""
    print("Running pytest suite...")
    cmd = [sys.executable, "-m", "pytest", "-v"]
    subprocess.run(cmd)


def cmd_demo(args):
    """Run an end-to-end live demonstration."""
    print("=" * 60)
    print("  ANGALIA SCRAPER - LIVE DEMONSTRATION")
    print("=" * 60)
    # 1. Run quick crawl with limit 2
    print("\n1. Crawling sample listings from 'myjobmag' (limit=2)...")
    cmd = [sys.executable, "-m", "scrapy", "crawl", "myjobmag", "-s", "CLOSESPIDER_ITEMCOUNT=2"]
    subprocess.run(cmd)

    # 2. Show status
    print("\n2. Database status after crawl:")
    cmd_status(args)

    # 3. Preview alerts
    print("\n3. Generating and previewing alert digest:")
    args.hours = 24
    args.dry_run = True
    args.channel = "all"
    cmd_alerts(args)

    print("\n[OK] Demonstration complete! All components verified operational.")


def main():
    parser = argparse.ArgumentParser(description="Angalia Scraper Management CLI")
    subparsers = parser.add_subparsers(dest="command", help="Sub-command to execute")

    # status
    subparsers.add_parser("status", help="Show SQLite database status and item counts")

    # crawl
    crawl_p = subparsers.add_parser("crawl", help="Run scrapers")
    crawl_p.add_argument("target", nargs="?", default="jobs", help="Spider name, 'jobs', 'products', or 'all'")
    crawl_p.add_argument("--limit", type=int, default=None, help="Maximum items to scrape per spider")

    # alerts
    alerts_p = subparsers.add_parser("alerts", help="Dispatch alerts")
    alerts_p.add_argument("--channel", choices=["all", "telegram", "email"], default="all")
    alerts_p.add_argument("--hours", type=int, default=24, help="Event lookback window in hours")
    alerts_p.add_argument("--dry-run", action="store_true", help="Preview alerts without sending")
    alerts_p.add_argument("--force", action="store_true", help="Bypass deduplication window")

    # worker
    subparsers.add_parser("worker", help="Run Celery worker")

    # beat
    subparsers.add_parser("beat", help="Run Celery beat scheduler")

    # test
    subparsers.add_parser("test", help="Run pytest suite")

    # demo
    subparsers.add_parser("demo", help="Run full end-to-end demonstration")

    args = parser.parse_args()

    if not args.command:
        # If no arguments provided, show status and usage
        cmd_status(args)
        print("\nAvailable commands:")
        print("  python run.py crawl [jobs|products|all|<spider>] [--limit N]")
        print("  python run.py alerts [--dry-run] [--channel telegram|email]")
        print("  python run.py status")
        print("  python run.py demo")
        print("  python run.py test")
        print("  python run.py worker")
        print("  python run.py beat\n")
        return

    commands = {
        "status": cmd_status,
        "crawl": cmd_crawl,
        "alerts": cmd_alerts,
        "worker": cmd_worker,
        "beat": cmd_beat,
        "test": cmd_test,
        "demo": cmd_demo,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
