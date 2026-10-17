"""Unit tests for configuration parsing, logging setup, and base spider middlewares."""

from scrapy.http import Request
from scrapy.spiders import Spider

from watchtower.config import Settings
from watchtower.logging import get_logger, setup_logging
from watchtower.spiders.base import BaseSpider, RandomUserAgentMiddleware, RotatingProxyMiddleware


def test_settings_validators() -> None:
    s = Settings(
        ALERT_TO_EMAILS="a@b.com, c@d.com,  ",
        PROXIES="http://proxy1:8080\nhttp://proxy2:8080",
    )
    assert s.ALERT_TO_EMAILS == ["a@b.com", "c@d.com"]
    assert len(s.PROXIES) == 2
    assert "http://proxy1:8080" in s.PROXIES

    s_empty = Settings(ALERT_TO_EMAILS="", PROXIES="")
    assert s_empty.ALERT_TO_EMAILS == []
    assert s_empty.PROXIES == []


def test_logging_setup() -> None:
    setup_logging()
    log = get_logger("test_logger")
    assert log is not None


def test_base_spider_middlewares() -> None:
    # 1. Random User Agent Middleware
    ua_mw = RandomUserAgentMiddleware(["Agent/1.0", "Agent/2.0"])
    req = Request("https://example.com")
    spider = Spider("dummy")
    ua_mw.process_request(req, spider)
    assert req.headers.get("User-Agent") in (b"Agent/1.0", b"Agent/2.0")

    # 2. Rotating Proxy Middleware
    proxy_mw = RotatingProxyMiddleware(["http://proxy1:8080"])
    req2 = Request("https://example.com")
    proxy_mw.process_request(req2, spider)
    assert req2.meta.get("proxy") == "http://proxy1:8080"


def test_base_spider_safe_extract() -> None:
    from scrapy.http import HtmlResponse

    resp = HtmlResponse(url="https://example.com", body="<html><body><h1 class='title'>Hello World</h1></body></html>", encoding="utf-8")
    spider = BaseSpider("dummy")

    # CSS extraction
    val1 = spider.safe_extract(resp, "h1.title::text")
    assert val1 == "Hello World"

    # XPath extraction
    val2 = spider.safe_extract(resp, "//h1/text()")
    assert val2 == "Hello World"

    # Default fallback
    val3 = spider.safe_extract(resp, "div.non-existent::text", default="Default Val")
    assert val3 == "Default Val"
