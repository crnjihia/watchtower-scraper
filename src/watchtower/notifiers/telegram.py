"""Telegram Bot API notification provider."""

import re
import time
from typing import List, Optional

import httpx

from watchtower.config import get_settings
from watchtower.logging import get_logger
from watchtower.schemas.alert import AlertPayload

logger = get_logger(__name__)


def escape_markdown_v2(text: Optional[str]) -> str:
    """Escape special MarkdownV2 reserved characters."""
    if not text:
        return ""
    # Characters that require escaping in Telegram MarkdownV2
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", str(text))


class TelegramNotifier:
    """Notifier for Telegram channels using official Bot API."""

    name = "telegram"

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        max_batch_size: int = 10,
        rate_limit_delay: float = 0.28,  # Respect 4 msg/sec rate limit
    ) -> None:
        settings = get_settings()
        self.bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or settings.TELEGRAM_CHAT_ID
        self.max_batch_size = max_batch_size
        self.rate_limit_delay = rate_limit_delay

    def is_configured(self) -> bool:
        """Check if required Telegram credentials are present."""
        return bool(self.bot_token and self.chat_id)

    def send(self, payloads: List[AlertPayload]) -> bool:
        """Send payloads as MarkdownV2 messages chunked into digests."""
        if not self.is_configured():
            logger.info("telegram_skipped_not_configured")
            return False

        if not payloads:
            return True

        chunks = [
            payloads[i : i + self.max_batch_size]
            for i in range(0, len(payloads), self.max_batch_size)
        ]

        success = True
        for chunk in chunks:
            message_text = self._format_digest(chunk)
            sent = self._send_message(message_text)
            if not sent:
                success = False
            time.sleep(self.rate_limit_delay)

        return success

    def _format_digest(self, chunk: List[AlertPayload]) -> str:
        """Format a batch of AlertPayloads into a single MarkdownV2 digest."""
        lines = ["🔔 *Watchtower Scraper Alert*", ""]

        for item in chunk:
            kind_icons = {
                "new_listing": "🆕",
                "price_drop": "📉",
                "price_increase": "📈",
                "removed": "❌",
                "updated": "🔄",
            }
            icon = kind_icons.get(item.kind, "ℹ️")
            title_escaped = escape_markdown_v2(item.title)
            # Tappable URL: [Title](URL)
            lines.append(f"{icon} *[{title_escaped}]({item.url})*")
            lines.append(f"• *Site:* {escape_markdown_v2(item.site.replace('_', ' ').title())}")

            if item.company:
                lines.append(f"• *Entity:* {escape_markdown_v2(item.company)}")

            if item.diff:
                if "old" in item.diff and "new" in item.diff:
                    old_p = escape_markdown_v2(f"KES {item.diff.get('old'):,.2f}" if item.diff.get('old') else "N/A")
                    new_p = escape_markdown_v2(f"KES {item.diff.get('new'):,.2f}" if item.diff.get('new') else "N/A")
                    pct_p = escape_markdown_v2(f"{item.diff.get('pct', 0.0):.1f}%")
                    lines.append(f"• *Price:* {old_p} ➔ {new_p} \\({pct_p}\\)")
                elif "price_kes" in item.diff and item.diff["price_kes"]:
                    prc = escape_markdown_v2(f"KES {item.diff['price_kes']:,.2f}")
                    lines.append(f"• *Listed Price:* {prc}")

            if item.summary:
                lines.append(f"• *Summary:* {escape_markdown_v2(item.summary)}")

            if item.tags:
                tag_str = " ".join([f"#{t.replace('-', '_')}" for t in item.tags])
                lines.append(f"_{escape_markdown_v2(tag_str)}_")

            lines.append("")

        return "\n".join(lines).strip()

    def _send_message(self, text: str) -> bool:
        """Execute HTTP POST request to Telegram send API."""
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "MarkdownV2",
            "disable_web_page_preview": False,
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(url, json=payload)
                if resp.status_code == 200:
                    logger.info("telegram_alert_sent", chat_id=self.chat_id)
                    return True
                else:
                    logger.error(
                        "telegram_api_error",
                        status_code=resp.status_code,
                        response=resp.text,
                    )
                    return False
        except Exception as e:
            logger.exception("telegram_send_exception", error=str(e))
            return False
