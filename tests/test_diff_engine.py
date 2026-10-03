import datetime

from angalia.diff.engine import diff
from angalia.items import JobItem, ProductItem


def make_product(price: float = 100.0, in_stock: bool = True, rating: float = 4.5) -> ProductItem:
    return ProductItem(
        source="jumia",
        external_id="prod-123",
        url="https://www.jumia.co.ke/p/test-123",
        scraped_at=datetime.datetime(2026, 1, 1, 12, 0, 0),
        name="Test Product",
        price=price,
        currency="KES",
        in_stock=in_stock,
        rating=rating,
    )


def make_job(
    salary: str = "KES 200,000",
    title: str = "Senior Engineer",
    location: str = "Nairobi",
    posted_at: datetime.datetime = datetime.datetime(2026, 1, 1, 12, 0, 0),
) -> JobItem:
    return JobItem(
        source="brightermonday",
        external_id="job-456",
        url="https://www.brightermonday.com/jobs/456",
        scraped_at=datetime.datetime(2026, 1, 1, 12, 0, 0),
        title=title,
        company="Acme Corp",
        location=location,
        job_type="Full Time",
        salary=salary,
        posted_at=posted_at,
        description_snippet="Great engineering role.",
    )


def test_diff_new_item():
    new = make_product(price=1000)
    events = diff(None, new)
    assert len(events) == 1
    ev = events[0]
    assert ev.type == "NEW"
    assert ev["type"] == "NEW"
    assert ev.source == "jumia"
    assert ev.external_id == "prod-123"
    assert ev.old is None
    assert ev.new is not None


def test_diff_removed_item():
    old = make_job()
    events = diff(old, None)
    assert len(events) == 1
    ev = events[0]
    assert ev.type == "REMOVED"
    assert ev.source == "brightermonday"
    assert ev.external_id == "job-456"
    assert ev.old is not None
    assert ev.new is None


def test_diff_both_none():
    assert diff(None, None) == []


def test_price_drop():
    old = make_product(price=150000)
    new = make_product(price=140000)
    events = diff(old, new)
    assert len(events) == 1
    ev = events[0]
    assert ev.type == "PRICE_DROP"
    assert ev.field == "price"
    assert ev.old == 150000
    assert ev.new == 140000


def test_price_rise():
    old = make_product(price=100000)
    new = make_product(price=120000)
    events = diff(old, new)
    assert len(events) == 1
    ev = events[0]
    assert ev.type == "PRICE_RISE"
    assert ev.field == "price"
    assert ev.old == 100000
    assert ev.new == 120000


def test_no_change():
    old = make_product(price=200000)
    new = make_product(price=200000)
    assert diff(old, new) == []


def test_job_field_update():
    old = make_job(salary="KES 200,000")
    new = make_job(salary="KES 250,000")
    events = diff(old, new)
    assert len(events) == 1
    ev = events[0]
    assert ev.type == "UPDATED"
    assert ev.field == "salary"
    assert ev.old == "KES 200,000"
    assert ev.new == "KES 250,000"


def test_multiple_field_updates():
    old = make_job(title="Engineer", location="Mombasa")
    new = make_job(title="Staff Engineer", location="Nairobi")
    events = diff(old, new)
    assert len(events) == 2
    fields_updated = {e.field for e in events}
    assert fields_updated == {"title", "location"}
    assert all(e.type == "UPDATED" for e in events)


def test_base_fields_ignored_in_update():
    old = make_job()
    new = make_job()
    new.scraped_at = datetime.datetime(2026, 1, 2, 12, 0, 0)
    new.content_hash = "custom-hash-diff"
    assert diff(old, new) == []
