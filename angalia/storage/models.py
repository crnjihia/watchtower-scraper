from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    JSON,
    UniqueConstraint,
    Index,
)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    source = Column(String, nullable=False)
    external_id = Column(String, nullable=False)
    url = Column(String, nullable=False)
    data = Column(JSON, nullable=False)  # full item payload
    content_hash = Column(String, nullable=False, index=True)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_source_external"),
        Index("ix_source_hash", "source", "content_hash"),
    )


class ItemHistory(Base):
    __tablename__ = "history"
    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, nullable=False, index=True)
    field = Column(String, nullable=False)
    old_value = Column(String)
    new_value = Column(String)
    changed_at = Column(DateTime, default=datetime.utcnow)


class AlertSent(Base):
    __tablename__ = "alerts_sent"
    id = Column(Integer, primary_key=True)
    source = Column(String, nullable=False)
    external_id = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "source", "external_id", "event_type", name="uq_alert_sent"
        ),
    )
