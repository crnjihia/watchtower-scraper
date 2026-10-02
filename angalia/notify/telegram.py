import os
import asyncio
import structlog
from typing import List, Dict
from telegram import Bot, ParseMode
from telegram.error import TelegramError

log = structlog.get_logger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    log.warning("Telegram credentials missing – notifications disabled")
    Bot = None  # type: ignore


async def _send_message(text: str):
    if Bot is None:
        return
    bot = Bot(token=BOT_TOKEN)
    try:
        await bot.send_message(
            chat_id=CHAT_ID,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
    except TelegramError as exc:
        log.error("telegram_send_error", error=str(exc))


def format_event(event: Dict) -> str:
    """Return a markdown‑formatted line for a single ChangeEvent."""
    emoji_map = {
        "NEW": "🆕",
        "PRICE_DROP": "📉",
        "PRICE_RISE": "📈",
        "UPDATED": "✏️",
        "REMOVED": "❌",
    }
    emoji = emoji_map.get(event["type"], "🔔")
    title = event.get("field") or "item"
    if event["type"] in ("PRICE_DROP", "PRICE_RISE"):
        value_part = f"*{event['old']} → {event['new']}*"
    elif event["type"] == "NEW":
        value_part = "*new*"
    elif event["type"] == "UPDATED":
        value_part = f"*{event['old']} → {event['new']}*"
    else:
        value_part = ""
    return f"{emoji} [{event['source'].title()}]({event['url']}): {title} {value_part}"


async def send_telegram_alerts(events: List[Dict]):
    """Batch‑send alerts grouped by source."""
    if Bot is None:
        log.info("Telegram bot not configured – skipping alerts")
        return

    messages = {}
    for ev in events:
        messages.setdefault(ev["source"], []).append(format_event(ev))

    tasks = [
        _send_message(f"*{src.upper()} updates*:\n" + "\n".join(lines))
        for src, lines in messages.items()
    ]
    await asyncio.gather(*tasks)
