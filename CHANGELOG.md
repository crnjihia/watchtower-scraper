# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-10-17

### Added
- **Multi-Source Kenyan Spiders**:
  - `brighter_monday`: Scrapes BrighterMonday Kenya job listings and details.
  - `fuzu`: Scrapes Fuzu Kenya job board vacancies and employers.
  - `myjobmag`: Scrapes MyJobMag Kenya job vacancies and descriptions.
  - `jumia`: Monitors watchlist products, pricing, stock status, and ratings on Jumia Kenya.
  - `kilimall`: Monitors watchlist products, pricing, and stock status on Kilimall Kenya.
- **Pure Differential State Engine (`angalia/diff`)**:
  - Deterministic `diff()` function emitting `NEW`, `REMOVED`, `PRICE_DROP`, `PRICE_RISE`, and `UPDATED` events without side-effects.
- **Multi-Stage Scrapy Item Pipelines**:
  - `ValidationPipeline`: Rejects listings missing mandatory schema attributes.
  - `DeduplicationPipeline`: Filters duplicate items across runs via SHA-256 `content_hash` over a configurable lookback window.
  - `DiffPipeline`: Automatically compares incoming listings against stored snapshots in SQLite.
  - `SQLiteStorePipeline`: Persists state in `items` table and writes detailed field transitions into `history` table.
- **Persistent Storage**:
  - Thread-safe SQLAlchemy 2.0 SQLite schema (`items`, `history`, and `alerts_sent` deduplication table).
- **Notification Services**:
  - `telegram`: Asynchronous Telegram Bot broadcaster with rich Markdown formatting, emojis (`🆕`, `📉`, `📈`, `✏️`), and 24-hour deduplication.
  - `email`: SendGrid daily HTML digest with Jinja2 templates and dynamic summary subjects.
- **Background Orchestration**:
  - Celery 5.4 + Redis Beat crontab scheduling:
    - Jobs scraped every 4 hours (`0 */4 * * *`)
    - Products scraped every 6 hours (`0 */6 * * *`)
    - Telegram alerts drained every 5 minutes (`*/5 * * * *`)
    - Daily email digest at 08:00 EAT (05:00 UTC)
    - Weekly stale item cleanup on Sundays
- **Unified Management CLI (`run.py`)**:
  - Subcommands: `status`, `crawl`, `alerts`, `worker`, `beat`, `test`, `demo`, `--version`.
- **GitHub Container Registry (GHCR) Package**:
  - Multi-arch Docker build (`linux/amd64`, `linux/arm64`) with non-root security (`appuser` UID 1000).
  - Flexible `entrypoint.sh` supporting Celery worker, beat, and CLI subcommands.
  - Pre-configured `docker-compose.ghcr.yml` for zero-build deployment.
- **Live Status & Documentation Dashboard (`docs/`)**:
  - GitHub Pages application with real-time metrics, spider health matrix, live event feed, interactive CLI simulator, and architecture guides.
- **Automated CI/CD**:
  - `.github/workflows/ci.yml`: Automated testing and linting across Python 3.11 and 3.12.
  - `.github/workflows/docker-publish.yml`: Automated GHCR package publishing on `main` and version tags (`v*`).
  - `.github/workflows/pages.yml`: Automated GitHub Pages deployment from `docs/`.
  - `.github/workflows/release.yml`: Automated GitHub release creation with wheel/sdist assets and SHA-256 checksums.

[Unreleased]: https://github.com/crnjihia/watchtower-scraper/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/crnjihia/watchtower-scraper/releases/tag/v0.1.0
