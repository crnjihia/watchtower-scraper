"""Base spider class and shared middlewares for ethical scraping."""

import random
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

import scrapy
from scrapy.http import Response

from watchtower.config import get_settings
from watchtower.logging import get_logger

logger = get_logger(__name__)


class RandomUserAgentMiddleware:
    """Downloader middleware that rotates User-Agents from configuration."""

    def __init__(self, user_agents: List[str]) -> None:
        self.user_agents = user_agents

    @classmethod
    def from_crawler(cls, crawler: Any) -> "RandomUserAgentMiddleware":
        settings = get_settings()
        agents = crawler.settings.getlist("USER_AGENTS") or settings.USER_AGENTS
        return cls(agents)

    def process_request(self, request: scrapy.Request, spider: scrapy.Spider) -> None:
        if self.user_agents:
            ua = random.choice(self.user_agents)
            request.headers["User-Agent"] = ua


class RotatingProxyMiddleware:
    """Downloader middleware that injects proxies if configured."""

    def __init__(self, proxies: List[str]) -> None:
        self.proxies = proxies

    @classmethod
    def from_crawler(cls, crawler: Any) -> "RotatingProxyMiddleware":
        settings = get_settings()
        proxies = crawler.settings.getlist("PROXIES") or settings.PROXIES
        return cls(proxies)

    def process_request(self, request: scrapy.Request, spider: scrapy.Spider) -> None:
        if self.proxies and "proxy" not in request.meta:
            proxy = random.choice(self.proxies)
            request.meta["proxy"] = proxy


class BaseSpider(scrapy.Spider):
    """Base class providing rate-limiting, custom middlewares, and canonical item formatting."""

    settings = get_settings()

    custom_settings: Dict[str, Any] = {
        "DOWNLOAD_DELAY": settings.DOWNLOAD_DELAY,
        "AUTOTHROTTLE_ENABLED": settings.AUTOTHROTTLE_ENABLED,
        "RANDOMIZE_DOWNLOAD_DELAY": settings.RANDOMIZE_DOWNLOAD_DELAY,
        "ROBOTSTXT_OBEY": settings.ROBOTSTXT_OBEY,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "DOWNLOAD_TIMEOUT": 15,
        "RETRY_TIMES": 3,
        "RETRY_HTTP_CODES": [500, 502, 503, 504, 522, 524, 408, 429],
        "ITEM_PIPELINES": {
            "watchtower.pipelines.normalize.NormalizePipeline": 100,
            "watchtower.pipelines.persist.PersistPipeline": 200,
        },
        "DOWNLOADER_MIDDLEWARES": {
            "watchtower.spiders.base.RandomUserAgentMiddleware": 400,
            "watchtower.spiders.base.RotatingProxyMiddleware": 410,
        },
    }

    def build_item(
        self,
        site: str,
        external_id: str,
        url: str,
        title: str,
        company: Optional[str] = None,
        price_kes: Optional[float] = None,
        currency: str = "KES",
        location: Optional[str] = None,
        posted_at: Optional[str] = None,
        category: Optional[str] = None,
        raw: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Construct canonical item dict with all standard fields."""
        return {
            "site": site,
            "external_id": str(external_id),
            "url": str(url),
            "title": str(title) if title else "Untitled",
            "company": company,
            "price_kes": price_kes,
            "currency": currency or "KES",
            "location": location,
            "posted_at": posted_at,
            "category": category,
            "raw": raw or {},
            "scraped_at": datetime.now(UTC).replace(tzinfo=None),
        }

    def safe_extract(self, response: Response, css_or_xpath: str, default: str = "") -> str:
        """Safely extract text using CSS or XPath selector without throwing exceptions."""
        try:
            if css_or_xpath.startswith("/") or css_or_xpath.startswith("("):
                extracted = response.xpath(css_or_xpath).get(default=default)
            else:
                extracted = response.css(css_or_xpath).get(default=default)
            return (extracted or "").strip()
        except Exception as e:
            self.logger.warning(f"Selector extraction error: {e}", selector=css_or_xpath)
            return default
