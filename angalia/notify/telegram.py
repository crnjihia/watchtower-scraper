import asyncio
import os
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def _get_item_display_name(event: dict[str, Any]) -> str:
    """Extract human-readable title or name from event payload."""
    # Check direct keys
    if event.get("title"):
        return str(event["title"])
    if event.get("name"):
        return str(event["name"])

    # Check new payload if dictionary
    new_data = event.get("new")
    if isinstance(new_data, dict):
        if new_data.get("title"):
            return str(new_data["title"])
        if new_data.get("name"):
            return str(new_data["name"])

    # Check old payload if dictionary
    old_data = event.get("old")
    if isinstance(old_data, dict):
        if old_data.get("title"):
            return str(old_data["title"])
        if old_data.get("name"):
            return str(old_data["name"])

    field = event.get("field")
    if field:
        return f"item ({field})"
    return "listing"


def format_event(event: dict[str, Any]) -> str:
    """Return a markdown-formatted message for a ChangeEvent."""
    emoji_map = {
        "NEW": "🆕",
        "PRICE_DROP": "📉",
        "PRICE_RISE": "📈",
        "UPDATED": "✏️",
        "REMOVED": "❌",
    }
    ev_type = event.get("type", "UPDATED")
    emoji = emoji_map.get(ev_type, "🔔")
    source_name = str(event.get("source", "angalia")).title()
    url = event.get("url", "#")
    item_name = _get_item_display_name(event)

    if ev_type == "NEW":
        detail = ""
        new_data = event.get("new")
        if isinstance(new_data, dict):
            if new_data.get("company"):
                detail = f" at *{new_data['company']}*"
            elif new_data.get("price") is not None:
                detail = f" — *{new_data.get('currency', 'KES')} {new_data['price']:,.2f}*"
        return f"{emoji} *[{source_name}]* [{item_name}]({url}){detail}"

    elif ev_type in ("PRICE_DROP", "PRICE_RISE"):
        old_val = event.get("old", 0)
        new_val = event.get("new", 0)
        direction = "dropped" if ev_type == "PRICE_DROP" else "increased"
        return f"{emoji} *[{source_name}]* [{item_name}]({url}): Price {direction} *{old_val} → {new_val}*"

    elif ev_type == "UPDATED":
        field = event.get("field", "attribute")
        old_val = event.get("old")
        new_val = event.get("new")
        return f"{emoji} *[{source_name}]* [{item_name}]({url}): *{field}* changed *{old_val} → {new_val}*"

    elif ev_type == "REMOVED":
        return f"{emoji} *[{source_name}]* [{item_name}]({url}): listing removed"

    return f"{emoji} *[{source_name}]* [{item_name}]({url})"


async def _send_message(text: str):
    """Low-level message dispatch with python-telegram-bot or test-mock support."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        sample = text[:60].encode("ascii", "replace").decode("ascii")
        logger.info("telegram_skipped_no_credentials", text_sample=sample)
        return

    try:
        from telegram import Bot
        from telegram.constants import ParseMode

        bot = Bot(token=bot_token)
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=False,
        )
    except Exception as exc:
        logger.error("telegram_send_error", error=str(exc))


def _filter_dedup_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter out alerts that were already sent in the last 24 hours."""
    from ..storage.db import get_session
    from ..storage.models import AlertSent

    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=24)
    filtered = []

    try:
        with get_session() as session:
            for ev in events:
                src = ev.get("source")
                ext_id = str(ev.get("external_id", ""))
                ev_type = ev.get("type")
                if not (src and ext_id and ev_type):
                    filtered.append(ev)
                    continue

                already_sent = (
                    session.query(AlertSent.id)
                    .filter(
                        AlertSent.source == src,
                        AlertSent.external_id == ext_id,
                        AlertSent.event_type == ev_type,
                        AlertSent.sent_at >= cutoff,
                    )
                    .first()
                )
                if not already_sent:
                    filtered.append(ev)
    except Exception as exc:
        logger.error("alert_dedup_query_error", error=str(exc))
        # If DB query fails, allow alerts to prevent silencing critical updates
        return events

    return filtered


def _record_alerts_sent(events: list[dict[str, Any]]):
    """Record sent alerts into SQLite alerts_sent table."""
    from ..storage.db import get_session
    from ..storage.models import AlertSent

    now = datetime.now(UTC).replace(tzinfo=None)
    try:
        with get_session() as session:
            for ev in events:
                src = ev.get("source")
                ext_id = str(ev.get("external_id", ""))
                ev_type = ev.get("type")
                if src and ext_id and ev_type:
                    entry = AlertSent(
                        source=src,
                        external_id=ext_id,
                        event_type=ev_type,
                        sent_at=now,
                    )
                    session.add(entry)
            session.commit()
    except Exception as exc:
        logger.error("alert_dedup_save_error", error=str(exc))


async def send_telegram_alerts(events: list[Any], check_dedup: bool = True) -> int:
    """
    Format and send alert messages grouped by source.
    Deduplicates against SQLite alerts_sent within 24h.
    """
    if not events:
        return 0

    # Normalize events to dictionaries if ChangeEvent dataclasses
    normalized = [e.to_dict() if hasattr(e, "to_dict") else e for e in events]

    if check_dedup:
        to_send = _filter_dedup_events(normalized)
    else:
        to_send = normalized

    if not to_send:
        logger.info("no_new_alerts_after_dedup", total=len(events))
        return 0

    # Group messages by source
    grouped: dict[str, list[str]] = {}
    for ev in to_send:
        src = ev.get("source", "angalia")
        line = format_event(ev)
        grouped.setdefault(src, []).append(line)

    tasks = []
    for src, lines in grouped.items():
        header = f"📢 *Angalia Alert — {src.upper()}*\n\n"
        body = "\n".join(lines)
        tasks.append(_send_message(header + body))

    await asyncio.gather(*tasks)

    # Record sent alerts
    _record_alerts_sent(to_send)
    logger.info("telegram_alerts_sent", count=len(to_send))
    return len(to_send)
