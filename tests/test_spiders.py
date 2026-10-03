from pathlib import Path

from scrapy.http import HtmlResponse, Request

from angalia.items import JobItem, ProductItem
from angalia.spiders.brighter_monday import BrighterMondaySpider
from angalia.spiders.fuzu import FuzuSpider
from angalia.spiders.jumia import JumiaSpider
from angalia.spiders.kilimall import KilimallSpider
from angalia.spiders.myjobmag import MyJobMagSpider

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


def _load_fixture(filename: str) -> str:
    return (FIXTURE_DIR / filename).read_text(encoding="utf-8")


# -------------------------------------------------------------------------
# BrighterMonday Spider Tests
# -------------------------------------------------------------------------

def test_brighter_monday_custom_settings():
    spider = BrighterMondaySpider()
    assert spider.custom_settings is not None
    assert spider.custom_settings.get("DOWNLOAD_DELAY") == 2
    assert spider.custom_settings.get("AUTOTHROTTLE_ENABLED") is True
    assert spider.custom_settings.get("ROBOTSTXT_OBEY") is True


def test_brighter_monday_parse_listings():
    html = _load_fixture("brighter_monday.html")
    resp = HtmlResponse(url="https://www.brightermonday.com/jobs", body=html, encoding="utf-8")
    spider = BrighterMondaySpider()
    results = list(spider.parse(resp))

    assert len(results) >= 2
    assert all(isinstance(r, Request) for r in results)
    # Check detail page request and next page pagination
    urls = [r.url for r in results]
    assert any("senior-python-engineer-101" in u for u in urls)
    assert any("page=2" in u for u in urls)


def test_brighter_monday_parse_job():
    html = _load_fixture("brighter_monday_job.html")
    resp = HtmlResponse(
        url="https://www.brightermonday.com/jobs/senior-python-engineer-101",
        body=html,
        encoding="utf-8",
    )
    spider = BrighterMondaySpider()
    items = list(spider.parse_job(resp))

    assert len(items) == 1
    job = items[0]
    assert isinstance(job, JobItem)
    assert job.source == "brightermonday"
    assert job.title == "Senior Python Engineer"
    assert job.company == "Safaricom PLC"
    assert job.location == "Nairobi, Kenya"
    assert job.job_type == "Full Time"
    assert job.salary == "KES 250,000 - 350,000"
    assert job.content_hash != ""


# -------------------------------------------------------------------------
# Fuzu Spider Tests
# -------------------------------------------------------------------------

def test_fuzu_custom_settings():
    spider = FuzuSpider()
    assert spider.custom_settings is not None
    assert spider.custom_settings.get("DOWNLOAD_DELAY") == 2


def test_fuzu_parse_listings():
    html = _load_fixture("fuzu.html")
    resp = HtmlResponse(url="https://www.fuzu.com/jobs", body=html, encoding="utf-8")
    spider = FuzuSpider()
    results = list(spider.parse(resp))

    assert len(results) >= 2
    assert all(isinstance(r, Request) for r in results)
    urls = [r.url for r in results]
    assert any("cloud-solutions-architect-201" in u for u in urls)
    assert any("page=2" in u for u in urls)


def test_fuzu_parse_job():
    html = _load_fixture("fuzu_job.html")
    resp = HtmlResponse(
        url="https://www.fuzu.com/jobs/cloud-solutions-architect-201",
        body=html,
        encoding="utf-8",
    )
    spider = FuzuSpider()
    items = list(spider.parse_job(resp))

    assert len(items) == 1
    job = items[0]
    assert isinstance(job, JobItem)
    assert job.source == "fuzu"
    assert job.title == "Cloud Solutions Architect"
    assert job.company == "Equity Bank"
    assert job.salary == "KES 300,000 - 450,000"


# -------------------------------------------------------------------------
# MyJobMag Spider Tests
# -------------------------------------------------------------------------

def test_myjobmag_custom_settings():
    spider = MyJobMagSpider()
    assert spider.custom_settings is not None
    assert spider.custom_settings.get("DOWNLOAD_DELAY") == 2


def test_myjobmag_parse_listings():
    html = _load_fixture("myjobmag.html")
    resp = HtmlResponse(url="https://www.myjobmag.co.ke/jobs", body=html, encoding="utf-8")
    spider = MyJobMagSpider()
    results = list(spider.parse(resp))

    assert len(results) >= 2
    assert all(isinstance(r, Request) for r in results)
    urls = [r.url for r in results]
    assert any("devops-engineer-301" in u for u in urls)
    assert any("page=2" in u for u in urls)


def test_myjobmag_parse_job():
    html = _load_fixture("myjobmag_job.html")
    resp = HtmlResponse(
        url="https://www.myjobmag.co.ke/jobs/devops-engineer-301",
        body=html,
        encoding="utf-8",
    )
    spider = MyJobMagSpider()
    items = list(spider.parse_job(resp))

    assert len(items) == 1
    job = items[0]
    assert isinstance(job, JobItem)
    assert job.source == "myjobmag"
    assert job.title == "DevOps Engineer"
    assert job.company == "M-KOPA"


# -------------------------------------------------------------------------
# Jumia Spider Tests
# -------------------------------------------------------------------------

def test_jumia_custom_settings():
    spider = JumiaSpider()
    assert spider.custom_settings is not None
    assert spider.custom_settings.get("DOWNLOAD_DELAY") == 2


def test_jumia_start_requests():
    spider = JumiaSpider()
    requests = list(spider.start_requests())
    assert len(requests) >= 1
    assert all(isinstance(r, Request) for r in requests)
    assert any("jumia.co.ke" in r.url for r in requests)


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
    product = items[0]
    assert isinstance(product, ProductItem)
    assert product.source == "jumia"
    assert "iPhone 13" in product.name
    assert product.price == 149999.0
    assert product.currency == "KES"
    assert product.in_stock is True
    assert product.rating == 4.6


# -------------------------------------------------------------------------
# Kilimall Spider Tests
# -------------------------------------------------------------------------

def test_kilimall_custom_settings():
    spider = KilimallSpider()
    assert spider.custom_settings is not None
    assert spider.custom_settings.get("DOWNLOAD_DELAY") == 2


def test_kilimall_start_requests():
    spider = KilimallSpider()
    requests = list(spider.start_requests())
    assert len(requests) >= 1
    assert all(isinstance(r, Request) for r in requests)
    assert any("kilimall.co.ke" in r.url for r in requests)


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
    product = items[0]
    assert isinstance(product, ProductItem)
    assert product.source == "kilimall"
    assert "iPhone 13" in product.name
    assert product.price == 152000.0
    assert product.currency == "KES"
    assert product.in_stock is True
    assert product.rating == 4.5
