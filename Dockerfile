# ------------------------------------------------------------
# Base image
# ------------------------------------------------------------
FROM python:3.11-slim

# System dependencies for Scrapy (libxml2, libxslt, etc.) and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libxml2-dev \
    libxslt1-dev \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
ARG UID=1000
ARG GID=1000
RUN groupadd -g $GID appgroup && \
    useradd -m -u $UID -g $GID -s /bin/bash appuser

WORKDIR /app

# Install python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir .

# Copy application source and configs
COPY README.md .
COPY angalia ./angalia
COPY config ./config
COPY tests ./tests
COPY scrapy.cfg .
COPY Makefile .
COPY .env.example .

# Prepare data directory for SQLite volume
RUN mkdir -p /app/data && chown -R appuser:appgroup /app

USER appuser

ENV PYTHONUNBUFFERED=1 \
    SQLITE_DB_PATH="sqlite:////app/data/angalia.db"

# Default command - Celery worker (overridden via docker-compose)
CMD ["celery", "-A", "angalia.celery_app.celery_app", "worker", "--loglevel=info"]
