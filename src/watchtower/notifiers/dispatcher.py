"""Alert dispatcher coordinating fan-out, deduplication, and notification status."""

from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy.orm import Session

from watchtower.db.models import ChangeEvent
from watchtower.db.repository import mark_event_notified
from watchtower.logging import get_logger
from watchtower.notifiers.base import BaseNotifier
from watchtower.notifiers.email import EmailNotifier
from watchtower.notifiers.telegram import TelegramNotifier
from watchtower.schemas.alert import AlertPayload

logger = get_logger(__name__)


def build_alert_payload(event: ChangeEvent) -> AlertPayload:
    """Build canonical AlertPayload from a ChangeEvent ORM object."""
    item = event.item
    site = item.site
    kind_str = event.kind.value if hasattr(event.kind, "value") else str(event.kind)
    diff = event.diff or {}

    summary = ""
    if kind_str == "new_listing":
        summary = f"New listing on {site.replace('_', ' ').title()}"
        if item.company:
            summary += f" by {item.company}"
    elif kind_str in ("price_drop", "price_increase"):
        direction = "dropped" if kind_str == "price_drop" else "increased"
        pct = diff.get("pct", 0.0)
        old_val = diff.get("old")
        new_val = diff.get("new")
        summary = f"Price {direction} by {pct:.1f}% (KES {old_val:,.2f} ➔ KES {new_val:,.2f})"
    elif kind_str == "removed":
        summary = "Listing removed or inactive (unseen for threshold)"
    else:
        summary = f"Item updated on {site}"

    tags = [site, kind_str, "watchtower"]
    if item.category:
        tags.append(item.category.lower().replace(" ", "_"))

    return AlertPayload(
        event_id=event.id,
        kind=kind_str,
        site=site,
        title=item.title,
        url=item.url,
        summary=summary,
        diff=diff,
        tags=tags,
        company=item.company,
        location=item.location,
        price_kes=diff.get("new") or diff.get("price_kes"),
    )


class NotificationDispatcher:
    """Dispatches alerts across configured channels with deduplication."""

    def __init__(self, notifiers: Optional[List[BaseNotifier]] = None) -> None:
        if notifiers is not None:
            self.notifiers = notifiers
        else:
            self.notifiers = [
                TelegramNotifier(),
                EmailNotifier(),
            ]
        # In-process deduplication cache: (event_id, channel_name)
        self._sent_keys: Set[Tuple[int, str]] = set()

    def dispatch_events(self, events: List[ChangeEvent], session: Session) -> Dict[str, int]:
        """Convert events to payloads, dedupe, fan-out to channels, and update database."""
        stats = {"total": len(events), "notified": 0, "skipped": 0, "errors": 0}
        if not events:
            return stats

        active_notifiers = [n for n in self.notifiers if n.is_configured()]
        if not active_notifiers:
            logger.warning("dispatcher_no_channels_configured", event_count=len(events))
            # If no channels configured, mark as notified to prevent backlog
            for ev in events:
                mark_event_notified(session, ev.id)
            session.commit()
            stats["skipped"] = len(events)
            return stats

        # Build payloads & filter out per-channel duplicates
        for notifier in active_notifiers:
            channel_payloads: List[AlertPayload] = []
            for ev in events:
                dedupe_key = (ev.id, notifier.name)
                if dedupe_key in self._sent_keys:
                    continue
                channel_payloads.append(build_alert_payload(ev))

            if channel_payloads:
                try:
                    success = notifier.send(channel_payloads)
                    if success:
                        for p in channel_payloads:
                            if p.event_id is not None:
                                self._sent_keys.add((p.event_id, notifier.name))
                    else:
                        stats["errors"] += 1
                except Exception as e:
                    logger.exception("notifier_dispatch_failed", channel=notifier.name, error=str(e))
                    stats["errors"] += 1

        # Mark all dispatched events as notified in the database
        for ev in events:
            mark_event_notified(session, ev.id)
            stats["notified"] += 1

        session.commit()
        return stats
