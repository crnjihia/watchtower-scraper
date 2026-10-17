"""Task for dispatching change event alerts across notification channels."""

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from watchtower.db.models import ChangeEvent
from watchtower.db.repository import get_unnotified_events
from watchtower.db.session import get_session_factory
from watchtower.logging import get_logger
from watchtower.notifiers.dispatcher import NotificationDispatcher
from watchtower.tasks.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(
    name="watchtower.tasks.notify.send_alert",
    bind=True,
    max_retries=5,
    default_retry_delay=30,
)
def send_alert(self: Any, change_event_id: Optional[int] = None) -> Dict[str, Any]:
    """Dispatch unnotified change event(s) to all configured channels with exponential backoff."""
    session_factory = get_session_factory()
    session: Session = session_factory()
    dispatcher = NotificationDispatcher()

    try:
        events: List[ChangeEvent] = []
        if change_event_id is not None:
            ev = session.get(ChangeEvent, change_event_id)
            if ev and ev.notified_at is None:
                events = [ev]
        else:
            events = list(get_unnotified_events(session, limit=100))

        if not events:
            return {"status": "no_events_to_notify"}

        stats = dispatcher.dispatch_events(events, session)
        return {"status": "dispatched", "stats": stats}

    except Exception as exc:
        logger.exception("send_alert_task_failure", error=str(exc))
        # Exponential backoff retry: 30s, 60s, 120s, 240s, 480s
        countdown = 30 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)
    finally:
        session.close()
