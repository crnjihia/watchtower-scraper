"""SQLAlchemy ORM models for Watchtower Scraper."""

import enum
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    """Return current UTC datetime without timezone info for clean SQLite/Postgres storage."""
    return datetime.now(UTC).replace(tzinfo=None)


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy models."""
    pass


class ChangeKind(str, enum.Enum):
    """Enumeration of detected change event types."""

    NEW_LISTING = "new_listing"
    PRICE_DROP = "price_drop"
    PRICE_INCREASE = "price_increase"
    REMOVED = "removed"
    UPDATED = "updated"


class Item(Base):
    """Canonical scraped item representing a job posting or an e-commerce product."""

    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False, index=True
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # Relationships
    snapshots: Mapped[List["ItemSnapshot"]] = relationship(
        "ItemSnapshot", back_populates="item", cascade="all, delete-orphan", order_by="desc(ItemSnapshot.scraped_at)"
    )
    change_events: Mapped[List["ChangeEvent"]] = relationship(
        "ChangeEvent", back_populates="item", cascade="all, delete-orphan", order_by="desc(ChangeEvent.created_at)"
    )

    __table_args__ = (
        UniqueConstraint("site", "external_id", name="uq_site_external_id"),
        Index("ix_item_site_active", "site", "active"),
    )

    def __repr__(self) -> str:
        return f"<Item(id={self.id}, site='{self.site}', external_id='{self.external_id}', active={self.active})>"


class ItemSnapshot(Base):
    """Point-in-time price record for historical tracking and diff calculation."""

    __tablename__ = "item_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True)
    price_kes: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False, index=True)

    # Relationship
    item: Mapped["Item"] = relationship("Item", back_populates="snapshots")

    def __repr__(self) -> str:
        return f"<ItemSnapshot(id={self.id}, item_id={self.item_id}, price_kes={self.price_kes}, scraped_at={self.scraped_at})>"


class ChangeEvent(Base):
    """Recorded delta/event for an item requiring alerting."""

    __tablename__ = "change_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True)
    kind: Mapped[ChangeKind] = mapped_column(
        Enum(ChangeKind, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        index=True,
    )
    diff: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False, index=True)
    notified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)

    # Relationship
    item: Mapped["Item"] = relationship("Item", back_populates="change_events")

    __table_args__ = (
        Index("ix_change_events_unnotified", "notified_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<ChangeEvent(id={self.id}, item_id={self.item_id}, kind='{self.kind}', notified_at={self.notified_at})>"


class SpiderRun(Base):
    """Audit log of individual spider crawl executions."""

    __tablename__ = "spider_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    spider: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    items_seen: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    errors: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="running", nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<SpiderRun(id={self.id}, spider='{self.spider}', status='{self.status}', items_seen={self.items_seen})>"
