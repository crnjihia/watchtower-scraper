"""Unit tests for notification providers and dispatcher with mocked transports."""

from typing import Any, List
from unittest.mock import MagicMock

import pytest

from watchtower.db.models import ChangeEvent, ChangeKind, Item
from watchtower.notifiers.dispatcher import NotificationDispatcher
from watchtower.notifiers.email import EmailNotifier
from watchtower.notifiers.telegram import TelegramNotifier, escape_markdown_v2
from watchtower.schemas.alert import AlertPayload


def test_telegram_escape_markdown_v2() -> None:
    raw = "Hello_World! Price: [KES 150.00] (New & Old) - 100% *bold*"
    escaped = escape_markdown_v2(raw)
    assert r"\_" in escaped
    assert r"\!" in escaped
    assert r"\[" in escaped
    assert r"\." in escaped
    assert r"\*" in escaped


def test_telegram_send_success(monkeypatch: pytest.MonkeyPatch) -> None:
    notifier = TelegramNotifier(
        bot_token="test_token_123",
        chat_id="12345678",
        max_batch_size=5,
        rate_limit_delay=0.0,
    )
    assert notifier.is_configured() is True

    payloads = [
        AlertPayload(
            event_id=1,
            kind="price_drop",
            site="jumia",
            title="iPhone 13 Pro",
            url="https://jumia.co.ke/p/iphone",
            summary="Price dropped by 10%",
            diff={"old": 100000.0, "new": 90000.0, "pct": 10.0},
            tags=["jumia", "tech"],
        )
    ]

    sent_requests: List[Any] = []

    class MockResponse:
        status_code = 200
        text = '{"ok": true}'

    def mock_post(url: str, json: Any = None, **kwargs: Any) -> MockResponse:
        sent_requests.append({"url": url, "json": json})
        return MockResponse()

    monkeypatch.setattr("httpx.Client.post", lambda self, url, **kwargs: mock_post(url, **kwargs))

    success = notifier.send(payloads)
    assert success is True
    assert len(sent_requests) == 1
    assert "https://api.telegram.org/bottest_token_123/sendMessage" in sent_requests[0]["url"]
    assert sent_requests[0]["json"]["chat_id"] == "12345678"
    assert "iPhone 13 Pro" in sent_requests[0]["json"]["text"]


def test_email_send_success(monkeypatch: pytest.MonkeyPatch) -> None:
    notifier = EmailNotifier(
        api_key="SG.fake_key",
        from_email="alerts@watchtower.io",
        to_emails=["reviewer@example.com"],
    )
    assert notifier.is_configured() is True

    payloads = [
        AlertPayload(
            event_id=2,
            kind="new_listing",
            site="brighter_monday",
            title="Senior Python Architect",
            url="https://brightermonday.co.ke/job/1",
            summary="New job posted by Safaricom",
            company="Safaricom",
            diff={"type": "new_listing"},
        )
    ]

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 202
    mock_client.mail.send.post.return_value = mock_response

    monkeypatch.setattr(
        "watchtower.notifiers.email.SendGridAPIClient",
        lambda key: MagicMock(client=mock_client),
    )

    success = notifier.send(payloads)
    assert success is True
    assert mock_client.mail.send.post.called


def test_dispatcher_deduplication_and_fanout(tmp_path: Any) -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from watchtower.db.models import Base

    db_path = f"sqlite:///{tmp_path}/test_dispatch.db"
    engine = create_engine(db_path)
    Base.metadata.create_all(engine)
    session = Session(engine)

    item = Item(
        site="jumia",
        external_id="ext-101",
        url="https://jumia.co.ke/101",
        title="Test Phone",
    )
    session.add(item)
    session.commit()

    event = ChangeEvent(
        item_id=item.id,
        kind=ChangeKind.PRICE_DROP,
        diff={"old": 50000.0, "new": 45000.0, "pct": 10.0},
    )
    session.add(event)
    session.commit()

    # Mocked notifier recording received payloads
    class SpyNotifier:
        name = "spy"

        def __init__(self) -> None:
            self.received_payloads: List[List[AlertPayload]] = []

        def is_configured(self) -> bool:
            return True

        def send(self, payloads: List[AlertPayload]) -> bool:
            self.received_payloads.append(payloads)
            return True

    spy = SpyNotifier()
    dispatcher = NotificationDispatcher(notifiers=[spy])

    try:
        # First dispatch
        stats1 = dispatcher.dispatch_events([event], session)
        assert stats1["notified"] == 1
        assert len(spy.received_payloads) == 1
        assert event.notified_at is not None

        # Second dispatch with the same event: deduplicated, should not send again!
        stats2 = dispatcher.dispatch_events([event], session)
        assert stats2["notified"] == 1
        assert len(spy.received_payloads) == 1  # Unchanged!
    finally:
        session.close()
        engine.dispose()
