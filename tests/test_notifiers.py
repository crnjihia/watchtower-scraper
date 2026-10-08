import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import angalia.storage.db as db_mod
from angalia.notify.email import (
    build_subject_and_summary,
    render_html,
    send_email_digest,
)
from angalia.notify.telegram import (
    format_event,
    send_telegram_alerts,
)
from angalia.storage.models import Base


@pytest.fixture
def isolated_alert_db(monkeypatch):
    """Provide isolated in-memory SQLite with StaticPool for alert dedup tests."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    from contextlib import contextmanager

    @contextmanager
    def mock_get_session(custom_session=None):
        sess = Session()
        try:
            yield sess
            sess.commit()
        except Exception:
            sess.rollback()
            raise
        finally:
            sess.close()

    monkeypatch.setattr(db_mod, "get_session", mock_get_session)
    monkeypatch.setattr(db_mod, "engine", engine)
    return engine, Session


def test_format_event_price_drop():
    ev = {
        "type": "PRICE_DROP",
        "source": "jumia",
        "external_id": "item-1",
        "field": "price",
        "old": 150000,
        "new": 140000,
        "url": "https://jumia.co.ke/p/item-1",
        "name": "iPhone 13",
    }
    txt = format_event(ev)
    assert "📉" in txt
    assert "[Jumia]" in txt
    assert "Price dropped" in txt
    assert "150000 → 140000" in txt
    assert "iPhone 13" in txt


def test_format_event_new_job():
    ev = {
        "type": "NEW",
        "source": "brightermonday",
        "external_id": "job-1",
        "url": "https://brightermonday.com/jobs/1",
        "new": {"title": "Staff Engineer", "company": "Safaricom"},
    }
    txt = format_event(ev)
    assert "🆕" in txt
    assert "[Brightermonday]" in txt
    assert "Staff Engineer" in txt
    assert "Safaricom" in txt


def test_render_email_html_and_subject():
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
            "name": "Samsung TV",
        },
    ]

    subject, summary = build_subject_and_summary(events)
    assert "Watchtower Daily:" in subject
    assert "1 new job" in subject
    assert "1 price drop" in subject

    html = render_html(events)
    assert "<table" in html
    assert "Data Analyst" in html
    assert "Samsung TV" in html
    assert "140000" in html


@pytest.mark.asyncio
async def test_telegram_send_and_dedup(isolated_alert_db, monkeypatch):
    sent_messages = []

    async def mock_send(text):
        sent_messages.append(text)

    monkeypatch.setattr("angalia.notify.telegram._send_message", mock_send)

    events = [
        {
            "type": "NEW",
            "source": "fuzu",
            "external_id": "fuzu-999",
            "url": "https://fuzu.com/jobs/999",
            "new": {"title": "Python Lead"},
        }
    ]

    # 1. First alert sent
    count1 = await send_telegram_alerts(events, check_dedup=True)
    assert count1 == 1
    assert len(sent_messages) == 1
    assert "Python Lead" in sent_messages[0]

    # 2. Duplicate alert within 24h is skipped
    count2 = await send_telegram_alerts(events, check_dedup=True)
    assert count2 == 0
    assert len(sent_messages) == 1  # No additional message sent


def test_send_email_digest_with_mock(isolated_alert_db, monkeypatch):
    events = [
        {
            "type": "NEW",
            "source": "jumia",
            "external_id": "jum-100",
            "url": "https://jumia.co.ke/p/100",
            "new": {"name": "Blender", "price": 4500},
        }
    ]

    class MockResponse:
        status_code = 202

    class MockSendGrid:
        def __init__(self, key):
            pass
        def send(self, message):
            return MockResponse()

    monkeypatch.setenv("SENDGRID_API_KEY", "SG.fake_key")
    monkeypatch.setattr("sendgrid.SendGridAPIClient", MockSendGrid)

    result = send_email_digest(events, check_dedup=False)
    assert result is not None
    assert "Blender" in result
