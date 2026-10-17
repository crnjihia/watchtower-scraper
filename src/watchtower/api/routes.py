"""API routes for system status, spider runs, and recorded change events."""

from datetime import UTC, datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from watchtower.db.repository import get_recent_changes, get_recent_runs
from watchtower.db.session import get_db_session

router = APIRouter()


@router.get("/")
def get_root() -> Dict[str, Any]:
    """Root endpoint providing service metadata and API navigation links."""
    return {
        "service": "Watchtower Scraper API",
        "version": "0.1.0",
        "description": "Ethical monitoring, differential state engine, and alerts for Kenyan markets",
        "documentation": "/docs",
        "endpoints": {
            "health": "/health",
            "runs": "/runs",
            "changes": "/changes",
            "interactive_docs": "/docs",
            "openapi_spec": "/openapi.json",
        },
    }


@router.get("/health")
def get_health(db: Session = Depends(get_db_session)) -> Dict[str, Any]:
    """Check API and database health status."""
    try:
        # Simple test query to ensure database connectivity
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {e}"

    return {
        "status": "ok" if db_status == "healthy" else "degraded",
        "timestamp": datetime.now(UTC).isoformat(),
        "database": db_status,
    }


@router.get("/runs")
def list_spider_runs(
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db_session),
) -> List[Dict[str, Any]]:
    """List recent spider crawl executions."""
    runs = get_recent_runs(db, limit=limit)
    return [
        {
            "id": r.id,
            "spider": r.spider,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "items_seen": r.items_seen,
            "errors": r.errors,
            "status": r.status,
        }
        for r in runs
    ]


@router.get("/changes")
def list_changes(
    limit: int = Query(default=50, ge=1, le=500),
    unnotified_only: bool = Query(default=False),
    db: Session = Depends(get_db_session),
) -> List[Dict[str, Any]]:
    """List recent change events detected across monitored platforms."""
    changes = get_recent_changes(db, limit=limit)
    if unnotified_only:
        changes = [c for c in changes if c.notified_at is None]

    return [
        {
            "id": c.id,
            "item_id": c.item_id,
            "site": c.item.site,
            "title": c.item.title,
            "url": c.item.url,
            "company": c.item.company,
            "kind": c.kind.value if hasattr(c.kind, "value") else str(c.kind),
            "diff": c.diff,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "notified_at": c.notified_at.isoformat() if c.notified_at else None,
        }
        for c in changes
    ]
