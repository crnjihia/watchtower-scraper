"""
Angalia Scraper Middlewares.

Handles custom spider and downloader middleware functionality.
Core anti-blocking behaviour is configured in settings.py:
- scrapy-user-agents (random realistic user agent per request)
- scrapy-rotating-proxies (IP rotation from PROXY_LIST)
- AutoThrottle + backoff retry on 429/503
"""

import structlog
from scrapy import signals

logger = structlog.get_logger(__name__)


class AngaliaSpiderMiddleware:
    """Spider middleware for signal handling and item/response logging."""

    @classmethod
    def from_crawler(cls, crawler):
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(s.spider_closed, signal=signals.spider_closed)
        return s

    def process_spider_input(self, response, spider):
        return None

    def process_spider_output(self, response, result, spider):
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        logger.error("spider_exception", spider=spider.name, url=response.url, error=str(exception))

    def spider_opened(self, spider):
        logger.info("spider_opened", spider=spider.name)

    def spider_closed(self, spider, reason):
        logger.info("spider_closed", spider=spider.name, reason=reason)
