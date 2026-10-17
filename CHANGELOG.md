# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-10-17

### Added
- **Production Architecture & Packaging (`src/watchtower`)**:
  - Clean modular architecture installed via `pyproject.toml` with strict typing and Pydantic v2 settings.
  - JSON structured logging with contextual binding for spider names and execution run IDs via `structlog`.
- **Target Spiders with Rate Limiting & Anti-Bot Protection**:
  - `brighter_monday`: Crawls Kenyan job postings with salary, job-type, and location extraction.
  - `fuzu`: Crawls Kenyan job vacancies with employer tracking and category mapping.
  - `my_job_mag`: Crawls Kenyan job vacancies with contract type and posting dates.
  - `jumia`: Monitors e-commerce product listings and prices on Jumia Kenya.
  - `kilimall`: Monitors e-commerce product listings and prices on Kilimall Kenya.
  - Built-in `BaseSpider` with AutoThrottle, randomized download delays, robots.txt obedience, and rotating User-Agents/Proxies.
- **Pipelines & Change Detection**:
  - `NormalizePipeline`: Sanitizes strings, normalizes diverse price formats to float KES, and parses ISO/relative timestamps.
  - `ChangeDetectionPipeline`: Pure diff engine detecting `new_listing`, `price_drop`, `price_increase`, `removed`, and threshold-filtered changes (`MIN_PRICE_DELTA_PCT`).
  - `PersistPipeline`: Idempotent persistence ensuring re-crawling identical items does not duplicate ChangeEvents or snapshots.
- **SQLAlchemy 2.0 Historical Persistence**:
  - `Item`, `ItemSnapshot`, `ChangeEvent`, and `SpiderRun` models with `uq_site_external_id` unique constraints.
  - Standalone `schema.sql` DDL for relational database provisioning.
- **Multi-Channel Alert Dispatcher**:
  - `TelegramNotifier`: Dispatches MarkdownV2 alerts with tappable URLs, 4 msg/sec rate limiting, and 10-item digest chunking.
  - `EmailNotifier`: Generates responsive HTML tables with diff snippets via SendGrid API.
  - `NotificationDispatcher`: Coordinates fan-out with per-channel deduplication by `(event_id, channel)`.
- **Celery Tasks & Celery Beat Scheduling**:
  - Daytime 15-minute job board crawls (06:00–22:00 EAT).
  - 30-minute e-commerce product crawls.
  - Automated weekly maintenance task (pruning snapshots >90 days, marking inactive items >24 hours).
  - Subprocess-isolated crawler process runner preventing Twisted reactor conflicts.
  - Exponential backoff alert retry policy (up to 5 retries).
- **FastAPI Read-Only Status & Audit API**:
  - Endpoints: `GET /health`, `GET /runs`, `GET /changes`.
- **Demonstration & Testing Utilities**:
  - `scripts/seed_demo.py`: Seeds demonstration items and allows immediate alert dispatch via `--notify`.
  - `scripts/test_core_flows.py`: Validates all 5 core application flows end-to-end.
  - Full test suite with 71 passing tests and >80% coverage on `src/watchtower`.
- **Docker & GitHub Container Registry**:
  - Multi-stage `Dockerfile` with non-root security (`appuser`).
  - Healthchecked `docker-compose.yml` with `redis`, `worker`, `beat`, `api`, and one-off `crawl` services.
  - Automated GitHub Actions for GHCR multi-arch container publishing and GitHub Release creation.

[Unreleased]: https://github.com/crnjihia/watchtower-scraper/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/crnjihia/watchtower-scraper/releases/tag/v0.1.0
