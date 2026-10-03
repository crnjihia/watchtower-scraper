from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(50), nullable=False)
    external_id = Column(String(255), nullable=False)
    url = Column(String(1024), nullable=False)
    data = Column(JSON, nullable=False)  # full item payload
    content_hash = Column(String(64), nullable=False, index=True)
    first_seen = Column(DateTime, default=utc_now, nullable=False)
    last_seen = Column(DateTime, default=utc_now, nullable=False, index=True)

    history = relationship(
        "ItemHistory", back_populates="item", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_source_external"),
        Index("ix_source_hash", "source", "content_hash"),
    )


class ItemHistory(Base):
    __tablename__ = "history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False, index=True)
    field = Column(String(100), nullable=False)
    old_value = Column(String(1024), nullable=True)
    new_value = Column(String(1024), nullable=True)
    changed_at = Column(DateTime, default=utc_now, nullable=False)

    item = relationship("Item", back_populates="history")


class AlertSent(Base):
    __tablename__ = "alerts_sent"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(50), nullable=False)
    external_id = Column(String(255), nullable=False)
    event_type = Column(String(50), nullable=False)
    sent_at = Column(DateTime, default=utc_now, nullable=False, index=True)

    __table_args__ = (
        Index("ix_alert_source_ext_type_sent", "source", "external_id", "event_type", "sent_at"),
    )
