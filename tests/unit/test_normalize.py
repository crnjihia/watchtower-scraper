"""Unit tests for the normalization pipeline."""

from datetime import UTC, datetime

from watchtower.pipelines.normalize import (
    NormalizePipeline,
    clean_text,
    normalize_datetime,
    normalize_price,
)


def test_clean_text() -> None:
    assert clean_text("  Senior   Python   Engineer \n\t ") == "Senior Python Engineer"
    assert clean_text("") is None
    assert clean_text(None) is None


def test_normalize_price_various_formats() -> None:
    assert normalize_price("KSh 149,999") == 149999.0
    assert normalize_price("KES 250,000 - 350,000") == 250000.0
    assert normalize_price("1,250.75 KES") == 1250.75
    assert normalize_price("KSh 12.500.00") == 12500.00
    assert normalize_price(5000) == 5000.0
    assert normalize_price(19.99) == 19.99
    assert normalize_price("Competitive") is None
    assert normalize_price(None) is None
    assert normalize_price("") is None


def test_normalize_datetime_relative_and_absolute() -> None:
    now_iso = normalize_datetime("just now")
    assert now_iso is not None
    assert "T" in now_iso

    yesterday_iso = normalize_datetime("Yesterday")
    assert yesterday_iso is not None

    hours_iso = normalize_datetime("3 hours ago")
    assert hours_iso is not None

    days_iso = normalize_datetime("2 days ago")
    assert days_iso is not None

    iso_str = "2026-10-17T12:00:00Z"
    parsed_iso = normalize_datetime(iso_str)
    assert parsed_iso == "2026-10-17T12:00:00"

    dt_obj = datetime(2026, 10, 15, 9, 30, tzinfo=UTC)
    assert normalize_datetime(dt_obj) == "2026-10-15T09:30:00"

    assert normalize_datetime("Invalid date string") is None
    assert normalize_datetime(None) is None


def test_normalize_pipeline_process_item() -> None:
    pipeline = NormalizePipeline()
    raw_item = {
        "site": "jumia",
        "external_id": "12345",
        "url": " https://jumia.co.ke/p/item-12345 ",
        "title": "  Apple iPhone 13 Pro   ",
        "company": " Apple Store ",
        "price_kes": "KSh 120,000",
        "location": " Nairobi ",
        "category": " Electronics ",
        "posted_at": "Yesterday",
    }

    processed = pipeline.process_item(raw_item, spider=None)

    assert processed["title"] == "Apple iPhone 13 Pro"
    assert processed["company"] == "Apple Store"
    assert processed["price_kes"] == 120000.0
    assert processed["location"] == "Nairobi"
    assert processed["category"] == "Electronics"
    assert processed["url"] == "https://jumia.co.ke/p/item-12345"
    assert processed["currency"] == "KES"
    assert processed["posted_at"] is not None
