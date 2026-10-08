import os
from pathlib import Path

import yaml

BASE_DIR = Path(__file__).resolve().parent.parent

# Load optional external settings (overrides defaults)
EXTRA_SETTINGS_PATH = BASE_DIR / "config" / "settings.yaml"
if EXTRA_SETTINGS_PATH.is_file():
    try:
        with open(EXTRA_SETTINGS_PATH, "r", encoding="utf-8") as f:
            extra_settings = yaml.safe_load(f) or {}
    except Exception:
        extra_settings = {}
else:
    extra_settings = {}

# ----------------------------------------------------------------------
# Scrapy core settings
# ----------------------------------------------------------------------
BOT_NAME = extra_settings.get("BOT_NAME", "angalia")
SPIDER_MODULES = extra_settings.get("SPIDER_MODULES", ["angalia.spiders"])
NEWSPIDER_MODULE = extra_settings.get("NEWSPIDER_MODULE", "angalia.spiders")

# Respect robots.txt (configurable via env or settings.yaml)
env_robots = os.getenv("ROBOTSTXT_OBEY")
if env_robots is not None:
    ROBOTSTXT_OBEY = env_robots.strip().lower() in ("true", "1", "yes")
else:
    ROBOTSTXT_OBEY = extra_settings.get("ROBOTSTXT_OBEY", True)

# Throttling / delay
DOWNLOAD_DELAY = float(extra_settings.get("DOWNLOAD_DELAY", os.getenv("DOWNLOAD_DELAY", "2.0")))
CONCURRENT_REQUESTS_PER_DOMAIN = int(extra_settings.get("CONCURRENT_REQUESTS_PER_DOMAIN", 1))

AUTOTHROTTLE_ENABLED = extra_settings.get(
    "AUTOTHROTTLE_ENABLED",
    os.getenv("AUTOTHROTTLE_ENABLED", "true").strip().lower() in ("true", "1", "yes"),
)
AUTOTHROTTLE_START_DELAY = float(extra_settings.get("AUTOTHROTTLE_START_DELAY", 2.0))
AUTOTHROTTLE_MAX_DELAY = float(extra_settings.get("AUTOTHROTTLE_MAX_DELAY", 10.0))
AUTOTHROTTLE_TARGET_CONCURRENCY = float(extra_settings.get("AUTOTHROTTLE_TARGET_CONCURRENCY", 1.0))
AUTOTHROTTLE_DEBUG = False

# Retry on common temporary errors with backoff on 429/503
RETRY_ENABLED = extra_settings.get("RETRY_ENABLED", True)
RETRY_TIMES = int(extra_settings.get("RETRY_TIMES", os.getenv("RETRY_TIMES", "3")))
RETRY_HTTP_CODES = extra_settings.get("RETRY_HTTP_CODES", [429, 503, 500, 502, 504])

# ----------------------------------------------------------------------
# Anti-blocking middlewares
# ----------------------------------------------------------------------
DOWNLOADER_MIDDLEWARES = {
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
    "scrapy_user_agents.middlewares.RandomUserAgentMiddleware": 400,
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": 550,
}

# Environment-driven rotating proxy list (comma-separated)
PROXY_LIST = os.getenv("PROXY_LIST", "").strip()
ROTATING_PROXY_LIST = [p.strip() for p in PROXY_LIST.split(",") if p.strip()]

# Enable rotating proxies only when proxies are provided
if ROTATING_PROXY_LIST:
    DOWNLOADER_MIDDLEWARES["rotating_proxies.middlewares.RotatingProxyMiddleware"] = 610
    DOWNLOADER_MIDDLEWARES["rotating_proxies.middlewares.BanDetectionMiddleware"] = 620


# User agent fallback identifying our bot ethically
USER_AGENT = "WatchtowerScraper/1.0 (+https://github.com/yourorg/watchtower-scraper; ethical-bot)"

# ----------------------------------------------------------------------
# Item pipelines
# ----------------------------------------------------------------------
ITEM_PIPELINES = {
    "angalia.pipelines.ValidationPipeline": 100,
    "angalia.pipelines.DeduplicationPipeline": 200,
    "angalia.pipelines.DiffPipeline": 300,
    "angalia.pipelines.SQLiteStorePipeline": 400,
}

# ----------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------
LOG_LEVEL = extra_settings.get("LOG_LEVEL", os.getenv("LOG_LEVEL", "INFO"))
LOG_FORMAT = "%(levelname)s %(asctime)s %(name)s %(message)s"
LOG_STDOUT = True

# ----------------------------------------------------------------------
# Celery / Redis
# ----------------------------------------------------------------------
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")

# Deduplication window in days
DEDUP_WINDOW_DAYS = int(os.getenv("DEDUP_WINDOW_DAYS", "3"))
