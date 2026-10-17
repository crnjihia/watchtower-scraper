"""Persistence pipeline for saving items, snapshots, and emitting change events."""

from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from watchtower.db.models import ChangeEvent
from watchtower.db.repository import (
    create_change_event,
    create_snapshot,
    get_item,
    get_latest_snapshot,
    upsert_item,
)
from watchtower.db.session import get_session_factory
from watchtower.logging import get_logger
from watchtower.pipelines.change_detect import detect_item_change

logger = get_logger(__name__)


class PersistPipeline:
    """Scrapy pipeline stage for database persistence and idempotent change recording."""

    def __init__(self) -> None:
        self.session_factory = get_session_factory()

    def process_item(self, item: Dict[str, Any], spider: Any) -> Dict[str, Any]:
        """Upsert item, record snapshot, and emit change event if applicable."""
        site = item.get("site", "unknown")
        external_id = item.get("external_id")

        if not external_id:
            logger.warning("persist_pipeline_skipped_missing_external_id", item=item)
            return item

        session: Session = self.session_factory()
        try:
            # 1. Fetch current database state for idempotency & diffing
            existing = get_item(session, site=site, external_id=external_id)
            latest_snapshot = get_latest_snapshot(session, existing.id) if existing else None
            price_kes = item.get("price_kes")

            # 2. Compute change
            change = detect_item_change(
                existing_item=existing,
                latest_snapshot=latest_snapshot,
                new_price=price_kes,
            )

            # 3. Upsert canonical item
            saved_item, is_new = upsert_item(
                session=session,
                site=site,
                external_id=external_id,
                url=item.get("url", ""),
                title=item.get("title", ""),
                company=item.get("company"),
                location=item.get("location"),
                category=item.get("category"),
            )

            # 4. If new or price changed, create snapshot & ChangeEvent
            created_event: Optional[ChangeEvent] = None
            if change is not None:
                kind, diff = change
                create_snapshot(session, item_id=saved_item.id, price_kes=price_kes)
                created_event = create_change_event(
                    session=session,
                    item_id=saved_item.id,
                    kind=kind,
                    diff=diff,
                )
                logger.info(
                    "change_event_emitted",
                    kind=kind.value,
                    site=site,
                    external_id=external_id,
                    diff=diff,
                )
            elif latest_snapshot is None and price_kes is not None:
                # Capture baseline snapshot if one wasn't present
                create_snapshot(session, item_id=saved_item.id, price_kes=price_kes)

            session.commit()

            # 5. Optionally trigger notification task asynchronously
            if created_event is not None:
                self._dispatch_event(created_event.id)

        except Exception as e:
            session.rollback()
            logger.exception("persist_pipeline_error", site=site, external_id=external_id, error=str(e))
            raise e
        finally:
            session.close()

        return item

    def _dispatch_event(self, event_id: int) -> None:
        """Enqueue alert task via Celery if available without crashing spider."""
        try:
            from watchtower.tasks.notify import send_alert
            send_alert.delay(event_id)
        except Exception:
            # In testing or standalone crawler mode without Redis, task enqueue failure is non-fatal
            pass
