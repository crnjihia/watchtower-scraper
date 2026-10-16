# ------------------------------------------------------------
# Base image
# ------------------------------------------------------------
FROM python:3.11-slim

# Labels for GitHub Container Registry (GHCR) and OCI specification
LABEL org.opencontainers.image.title="watchtower-scraper" \
      org.opencontainers.image.description="Ethical Scrapy scraper and market intelligence engine for Kenyan job boards and e-commerce" \
      org.opencontainers.image.url="https://github.com/crnjihia/watchtower-scraper" \
      org.opencontainers.image.source="https://github.com/crnjihia/watchtower-scraper" \
      org.opencontainers.image.licenses="MIT"

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

# Copy application source, configs, and runner
COPY README.md .
COPY run.py .
COPY entrypoint.sh .
COPY angalia ./angalia
COPY config ./config
COPY tests ./tests
COPY scrapy.cfg .
COPY Makefile .
COPY .env.example .

# Prepare data directory for SQLite volume & set permissions
RUN mkdir -p /app/data && \
    chmod +x /app/entrypoint.sh && \
    chown -R appuser:appgroup /app

USER appuser

ENV PYTHONUNBUFFERED=1 \
    SQLITE_DB_PATH="sqlite:////app/data/angalia.db"

# Container entrypoint routes to run.py or directly executes custom command
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command - Celery worker (overridden with 'beat', 'crawl jobs', etc.)
CMD ["worker"]
