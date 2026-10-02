import datetime
import pytest
from angalia.diff.engine import diff
from angalia.items import ProductItem

def make_item(price):
    return ProductItem(
        source="jumia",
        external_id="123",
        url="https://example.com/item/123",
        scraped_at=datetime.datetime.utcnow(),
        name="Test Product",
        price=price,
        currency="KES",
        in_stock=True,
        rating=4.5,
    )

def test_price_drop():
    old = make_item(150000)
    new = make_item(140000)
    events = diff(old, new)
    assert len(events) == 1
    ev = events[0]
    assert ev["type"] == "PRICE_DROP"
    assert ev["old"] == 150000
    assert ev["new"] == 140000

def test_price_rise():
    old = make_item(100000)
    new = make_item(110000)
    events = diff(old, new)
    assert events[0]["type"] == "PRICE_RISE"

def test_no_change():
    old = make_item(200000)
    new = make_item(200000)
    events = diff(old, new)
    assert events == []
