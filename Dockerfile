# ============================================================
# Stage 1: Build virtual environment and wheels
# ============================================================
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libxml2-dev \
    libxslt1-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir .

# ============================================================
# Stage 2: Runtime image with non-root user
# ============================================================
FROM python:3.11-slim AS runtime

LABEL org.opencontainers.image.title="watchtower-scraper" \
      org.opencontainers.image.description="Production-grade scraper for Kenyan job boards and e-commerce platforms" \
      org.opencontainers.image.licenses="MIT"

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    DATABASE_URL="sqlite:////app/data/watchtower.db" \
    REDIS_URL="redis://redis:6379/0"

# Create non-root app user
ARG UID=1000
ARG GID=1000
RUN groupadd -g $GID appuser && \
    useradd -m -u $UID -g $GID -s /bin/bash appuser

WORKDIR /app

# Copy application artifacts
COPY pyproject.toml README.md schema.sql ./
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY config/ ./config/

# Install watchtower package in editable mode within virtualenv
RUN pip install --no-cache-dir --no-deps -e .

# Create volume directories & chown
RUN mkdir -p /app/data && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["celery", "-A", "watchtower.tasks.celery_app", "worker", "--loglevel=INFO"]
