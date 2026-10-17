"""Task for triggering and managing Scrapy spider execution."""

import multiprocessing
from typing import Any, Dict

import structlog
from scrapy.crawler import CrawlerProcess

from watchtower.db.repository import create_spider_run, finish_spider_run
from watchtower.db.session import get_session_factory
from watchtower.logging import get_logger
from watchtower.spiders import (
    BrighterMondaySpider,
    FuzuSpider,
    JumiaSpider,
    KilimallSpider,
    MyJobMagSpider,
)
from watchtower.tasks.celery_app import celery_app

logger = get_logger(__name__)

SPIDER_REGISTRY = {
    "brighter_monday": BrighterMondaySpider,
    "fuzu": FuzuSpider,
    "my_job_mag": MyJobMagSpider,
    "myjobmag": MyJobMagSpider,
    "jumia": JumiaSpider,
    "kilimall": KilimallSpider,
}


def _execute_crawl_in_process(spider_cls: Any, return_dict: Dict[str, Any]) -> None:
    """Run Scrapy CrawlerProcess in an isolated subprocess to prevent Twisted reactor conflicts."""
    try:
        process = CrawlerProcess(
            settings={
                "LOG_LEVEL": "INFO",
                "REQUEST_FINGERPRINTER_IMPLEMENTATION": "2.7",
            }
        )
        process.crawl(spider_cls)
        process.start()

        # Extract stats from crawler
        stats = {}
        for crawler in process.crawlers:
            stats = crawler.stats.get_stats()
            break

        return_dict["items_seen"] = stats.get("item_scraped_count", 0)
        return_dict["errors"] = stats.get("log_count/ERROR", 0)
        return_dict["status"] = "completed"
    except Exception as exc:
        return_dict["status"] = "failed"
        return_dict["error"] = str(exc)
        return_dict["items_seen"] = 0
        return_dict["errors"] = 1


@celery_app.task(name="watchtower.tasks.crawl.run_spider", bind=True)
def run_spider(self: Any, spider_name: str) -> Dict[str, Any]:
    """Execute a registered spider, audit the run in DB, and return outcome summary."""
    spider_cls = SPIDER_REGISTRY.get(spider_name.lower())
    if not spider_cls:
        logger.error("spider_not_found", spider_name=spider_name)
        return {"error": f"Unknown spider: {spider_name}", "status": "failed"}

    session_factory = get_session_factory()
    session = session_factory()

    # Audit run start in database
    run_record = create_spider_run(session, spider=spider_name)
    session.commit()
    run_id = run_record.id

    # Bind structured logging context
    structlog.contextvars.bind_contextvars(spider=spider_name, run_id=run_id)
    logger.info("spider_run_started", spider=spider_name, run_id=run_id)

    manager = multiprocessing.Manager()
    return_dict = manager.dict()

    p = multiprocessing.Process(
        target=_execute_crawl_in_process,
        args=(spider_cls, return_dict),
    )
    p.start()
    p.join(timeout=3600)  # 1 hour maximum run time

    if p.is_alive():
        p.terminate()
        p.join()
        status = "timed_out"
        items_seen = return_dict.get("items_seen", 0)
        errors = return_dict.get("errors", 1) + 1
    else:
        status = return_dict.get("status", "completed")
        items_seen = return_dict.get("items_seen", 0)
        errors = return_dict.get("errors", 0)

    # Audit run finish
    finish_spider_run(
        session=session,
        run_id=run_id,
        items_seen=items_seen,
        errors=errors,
        status=status,
    )
    session.commit()
    session.close()

    logger.info(
        "spider_run_finished",
        spider=spider_name,
        run_id=run_id,
        items_seen=items_seen,
        errors=errors,
        status=status,
    )

    return {
        "run_id": run_id,
        "spider": spider_name,
        "items_seen": items_seen,
        "errors": errors,
        "status": status,
    }
