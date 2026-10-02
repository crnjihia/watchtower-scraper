import datetime
from pathlib import Path
import pytest
from scrapy.http import HtmlResponse, Request
from angalia.spiders.brighter_monday import BrighterMondaySpider
from angalia.spiders.fuzu import FuzuSpider
from angalia.spiders.myjobmag import MyJobMagSpider
from angalia.spiders.jumia import JumiaSpider
from angalia.spiders.kilimall import KilimallSpider

FIXTURE_DIR = Path(__file__).parent / "fixtures"

def _load_fixture(name):
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")

def test_brighter_monday_parse():
    html = _load_fixture("brighter_monday.html")
    resp = HtmlResponse(url="https://www.brightermonday.com/jobs", body=html, encoding="utf-8")
    spider = BrighterMondaySpider()
    results = list(spider.parse(resp))
    assert any(isinstance(r, Request) for r in results)

def test_fuzu_parse():
    html = _load_fixture("fuzu.html")
    resp = HtmlResponse(url="https://www.fuzu.com/jobs", body=html, encoding="utf-8")
    spider = FuzuSpider()
    results = list(spider.parse(resp))
    assert any(isinstance(r, Request) for r in results)

def test_myjobmag_parse():
    html = _load_fixture("myjobmag.html")
    resp = HtmlResponse(url="https://www.myjobmag.co.ke/jobs", body=html, encoding="utf-8")
    spider = MyJobMagSpider()
    results = list(spider.parse(resp))
    assert any(isinstance(r, Request) for r in results)

def test_jumia_parse_product():
    html = _load_fixture("jumia_product.html")
    resp = HtmlResponse(
        url="https://www.jumia.co.ke/p/phone-iphone-13-pro-max-512gb-blue-5555555",
        body=html,
        encoding="utf-8",
    )
    spider = JumiaSpider()
    items = list(spider.parse_product(resp))
    assert len(items) == 1
    item = items[0]
    assert item.name == "iPhone 13 Pro Max 512GB – Blue"
    assert item.price == 149999.0
    assert item.in_stock is True

def test_kilimall_parse_product():
    html = _load_fixture("kilimall_product.html")
    resp = HtmlResponse(
        url="https://www.kilimall.co.ke/p/iphone-13-pro-max-512gb-blue-111111",
        body=html,
        encoding="utf-8",
    )
    spider = KilimallSpider()
    items = list(spider.parse_product(resp))
    assert len(items) == 1
    item = items[0]
    assert item.name == "iPhone 13 Pro Max 512GB – Blue"
    assert item.price == 152000.0
    assert item.in_stock is True
