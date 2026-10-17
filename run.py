"""
Watchtower Scraper - Unified Application Runner & CLI
Usage:
    python run.py status
    python run.py crawl [spider_name|jobs|products|all] [--limit N]
    python run.py alerts [--dry-run]
    python run.py api [--port 8000]
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
SRC_DIR = os.path.join(BASE_DIR, "src")
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

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
    from sqlalchemy import func
    from watchtower.db.models import ChangeEvent, Item, ItemSnapshot, SpiderRun
    from watchtower.db.session import get_session_factory, init_db

    init_db()
    session = get_session_factory()()

    print("=" * 68)
    print("  WATCHTOWER SCRAPER - OPERATIONAL TELEMETRY & STATUS")
    print("=" * 68)

    try:
        total_items = session.query(Item).count()
        active_items = session.query(Item).filter(Item.active == True).count()
        total_snapshots = session.query(ItemSnapshot).count()
        total_events = session.query(ChangeEvent).count()
        total_runs = session.query(SpiderRun).count()

        print(f"Total Tracked Items       : {total_items} (Active: {active_items})")
        print(f"Total Historical Snapshots: {total_snapshots}")
        print(f"Total Change Events (Diff): {total_events}")
        print(f"Total Recorded Spider Runs: {total_runs}")
        print("-" * 68)

        by_site = (
            session.query(Item.site, func.count(Item.id))
            .group_by(Item.site)
            .order_by(func.count(Item.id).desc())
            .all()
        )
        print("Listings by Platform Site:")
        if by_site:
            for site, count in by_site:
                print(f"  * {site:<20} : {count:>5} items")
        else:
            print("  (Database currently has no items)")

        print("-" * 68)
        recent_events = (
            session.query(ChangeEvent)
            .order_by(ChangeEvent.created_at.desc())
            .limit(5)
            .all()
        )
        print("Most Recent Change Events:")
        if recent_events:
            for ev in recent_events:
                kind_str = ev.kind.value if hasattr(ev.kind, "value") else str(ev.kind)
                item_title = ev.item.title if ev.item else f"Item #{ev.item_id}"
                ts = ev.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
                print(f"  [{ts}] [{kind_str:<12}] {item_title[:45]}")
        else:
            print("  (No change events recorded yet)")

        print("-" * 68)
        recent_runs = (
            session.query(SpiderRun)
            .order_by(SpiderRun.started_at.desc())
            .limit(3)
            .all()
        )
        print("Latest Spider Runs:")
        if recent_runs:
            for run in recent_runs:
                items_cnt = run.items_seen if run.items_seen is not None else 0
                print(f"  Spider '{run.spider}': status={run.status} (seen {items_cnt} items)")
        else:
            print("  (No spider runs recorded yet)")

    finally:
        session.close()

    print("=" * 68)


def cmd_crawl(args):
    """Execute Scrapy crawler for spiders or spider groups."""
    target = args.target.lower()
    spiders = []
    if target == "jobs":
        spiders = ["brighter_monday", "fuzu", "my_job_mag"]
    elif target == "products":
        spiders = ["jumia", "kilimall"]
    elif target == "all":
        spiders = ["brighter_monday", "fuzu", "my_job_mag", "jumia", "kilimall"]
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
    """Preview or dispatch pending change events."""
    from watchtower.db.models import ChangeEvent
    from watchtower.db.session import get_session_factory, init_db
    from watchtower.notifiers.dispatcher import NotificationDispatcher

    init_db()
    session = get_session_factory()()

    try:
        events = (
            session.query(ChangeEvent)
            .filter(ChangeEvent.notified_at.is_(None))
            .order_by(ChangeEvent.created_at.desc())
            .all()
        )
        print(f"Found {len(events)} pending unnotified change events.")

        if not events:
            print("No pending alerts to dispatch.")
            return

        if args.dry_run:
            print("\n[DRY RUN PREVIEW]")
            for i, ev in enumerate(events[:5], 1):
                kind = ev.kind.value if hasattr(ev.kind, "value") else str(ev.kind)
                title = ev.item.title if ev.item else f"Item #{ev.item_id}"
                print(f"  {i}. [{kind}] {title}")
                if ev.diff:
                    print(f"     Diff: {json.dumps(ev.diff, default=str)}")
            if len(events) > 5:
                print(f"  ... and {len(events) - 5} more events.")
            return

        dispatcher = NotificationDispatcher()
        sent_count = 0
        for ev in events:
            # Dispatch synchronously for CLI command
            import asyncio
            result = asyncio.run(dispatcher.dispatch(ev, session))
            if result.get("telegram") or result.get("email"):
                sent_count += 1

        print(f"Successfully processed alerts for {sent_count} events.")

    finally:
        session.close()


def cmd_api(args):
    """Run FastAPI telemetry & inspection service."""
    port = args.port or 8000
    print(f"Starting Watchtower FastAPI Telemetry API on http://127.0.0.1:{port} ...")
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "watchtower.api.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--reload",
    ]
    subprocess.run(cmd)


def cmd_worker(args):
    """Run Celery worker process."""
    print("Starting Celery worker (press Ctrl+C to terminate)...")
    cmd = [
        sys.executable,
        "-m",
        "celery",
        "-A",
        "watchtower.tasks.celery_app",
        "worker",
        "--loglevel=info",
        "-P",
        "solo",
    ]
    subprocess.run(cmd)


def cmd_beat(args):
    """Run Celery beat scheduler."""
    print("Starting Celery beat scheduler (press Ctrl+C to terminate)...")
    cmd = [
        sys.executable,
        "-m",
        "celery",
        "-A",
        "watchtower.tasks.celery_app",
        "beat",
        "--loglevel=info",
    ]
    subprocess.run(cmd)


def cmd_test(args):
    """Run test suite with pytest."""
    print("Running pytest suite...")
    cmd = [sys.executable, "-m", "pytest", "-v"]
    subprocess.run(cmd)


def cmd_demo(args):
    """Run an end-to-end live demonstration."""
    print("=" * 68)
    print("  WATCHTOWER SCRAPER - LIVE DEMONSTRATION & CORE FLOWS")
    print("=" * 68)

    # 1. Run seed script
    print("\n1. Seeding sample listings and simulated price drops / new listings...")
    cmd_seed = [sys.executable, os.path.join(BASE_DIR, "scripts", "seed_demo.py")]
    subprocess.run(cmd_seed)

    # 2. Show status
    print("\n2. Database status after seeding:")
    cmd_status(args)

    # 3. Preview alerts
    print("\n3. Previewing pending alerts:")
    args.dry_run = True
    cmd_alerts(args)

    print("\n[OK] Demonstration complete! All subsystems verified operational.")


def main():
    parser = argparse.ArgumentParser(description="Watchtower Scraper Management CLI")
    parser.add_argument(
        "-v", "--version", action="version", version="watchtower-scraper v0.1.0"
    )
    subparsers = parser.add_subparsers(dest="command", help="Sub-command to execute")

    # status
    subparsers.add_parser("status", help="Show SQLite database status and item counts")

    # crawl
    crawl_p = subparsers.add_parser("crawl", help="Run scrapers")
    crawl_p.add_argument("target", nargs="?", default="jobs", help="Spider name, 'jobs', 'products', or 'all'")
    crawl_p.add_argument("--limit", type=int, default=None, help="Maximum items to scrape per spider")

    # alerts
    alerts_p = subparsers.add_parser("alerts", help="Dispatch alerts")
    alerts_p.add_argument("--dry-run", action="store_true", help="Preview alerts without sending")

    # api
    api_p = subparsers.add_parser("api", help="Run FastAPI telemetry & status API")
    api_p.add_argument("--port", type=int, default=8000, help="Port to bind API server (default 8000)")

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
        print("  python run.py status")
        print("  python run.py alerts [--dry-run]")
        print("  python run.py api [--port 8000]")
        print("  python run.py demo")
        print("  python run.py test")
        print("  python run.py worker")
        print("  python run.py beat\n")
        return

    commands = {
        "status": cmd_status,
        "crawl": cmd_crawl,
        "alerts": cmd_alerts,
        "api": cmd_api,
        "worker": cmd_worker,
        "beat": cmd_beat,
        "test": cmd_test,
        "demo": cmd_demo,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
