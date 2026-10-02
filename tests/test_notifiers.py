import asyncio
import pytest
from angalia.notify.telegram import format_event, _send_message
from angalia.notify.email import render_html, send_email_digest

@pytest.mark.asyncio
async def test_format_event():
    ev = {
        "type": "PRICE_DROP",
        "source": "jumia",
        "field": "price",
        "old": 150000,
        "new": 140000,
        "url": "https://example.com/item/1",
    }
    txt = format_event(ev)
    assert "📉" in txt
    assert "[JUMIA]" in txt
    assert "*150000 → 140000*" in txt

def test_render_email_html():
    events = [
        {
            "type": "NEW",
            "source": "fuzu",
            "field": None,
            "old": None,
            "new": {"title": "Data Analyst"},
            "url": "https://fuzu.com/job/123",
        },
        {
            "type": "PRICE_DROP",
            "source": "jumia",
            "field": "price",
            "old": 150000,
            "new": 140000,
            "url": "https://jumia.co.ke/p/1",
        },
    ]
    html = render_html(events)
    assert "<table" in html
    assert "price" in html
    assert "Data Analyst" in html

@pytest.mark.asyncio
async def test_telegram_send_message(monkeypatch):
    sent = {}
    async def fake_send_message(text):
        sent["msg"] = text
    monkeypatch.setattr("angalia.notify.telegram._send_message", fake_send_message)
    await _send_message("test")
    assert sent["msg"] == "test"
