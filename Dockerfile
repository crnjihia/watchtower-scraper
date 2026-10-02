# ------------------------------------------------------------
# Base image
# ------------------------------------------------------------
FROM python:3.11-slim

# System deps for Scrapy (libxml2, libxslt, etc.) and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libxml2-dev \
    libxslt1-dev \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non‑root user
ARG UID=1000
ARG GID=1000
RUN groupadd -g $GID appgroup && \
    useradd -m -u $UID -g $GID -s /bin/bash appuser
WORKDIR /app
COPY pyproject.toml .
COPY README.md .
COPY angalia ./angalia
COPY config ./config
COPY tests ./tests
COPY scrapy.cfg .
COPY docker-compose.yml .
COPY Makefile .
COPY .env.example .

# Install python dependencies
RUN pip install --no-cache-dir poetry && \
    poetry export -f requirements.txt --output requirements.txt && \
    pip install --no-cache-dir -r requirements.txt && \
    rm -rf /root/.cache

# Switch to non‑root user
USER appuser

# Default command – run Celery beat (overridden via Docker‑Compose)
CMD ["celery", "-A", "angalia.celery_app.celery_app", "beat", "--loglevel=info"]
