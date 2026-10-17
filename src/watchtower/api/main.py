"""FastAPI entry point for Watchtower Scraper status & inspection API."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI

from watchtower.api.routes import router
from watchtower.config import get_settings
from watchtower.db.session import init_db
from watchtower.logging import get_logger, setup_logging

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle management."""
    setup_logging()
    init_db()
    logger.info("watchtower_api_started")
    yield
    logger.info("watchtower_api_stopped")


app = FastAPI(
    title="Watchtower Scraper API",
    description="Read-only status and audit API for Watchtower Scraper monitoring system",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router)


def run() -> None:
    """Run API server via Uvicorn CLI entry point."""
    settings = get_settings()
    uvicorn.run("watchtower.api.main:app", host="0.0.0.0", port=settings.HTTP_PORT, reload=False)


if __name__ == "__main__":
    run()
