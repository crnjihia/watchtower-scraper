import os
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent

# Load optional external settings (overrides defaults)
EXTRA_SETTINGS_PATH = BASE_DIR / "config" / "settings.yaml"
if EXTRA_SETTINGS_PATH.is_file():
    with open(EXTRA_SETTINGS_PATH, "r", encoding="utf-8") as f:
        extra_settings = yaml.safe_load(f) or {}
else:
    extra_settings = {}

# ----------------------------------------------------------------------
# Scrapy core settings
# ----------------------------------------------------------------------
BOT_NAME = extra_settings.get("BOT_NAME", "angalia")
SPIDER_MODULES = extra_settings.get("SPIDER_MODULES", ["angalia.spiders"])
NEWSPIDER_MODULE = extra_settings.get("NEWSPIDER_MODULE", "angalia.spiders")
ROBOTSTXT_OBEY = extra_settings.get("ROBOTSTXT_OBEY", True)

# Throttling / delay
DOWNLOAD_DELAY = extra_settings.get("DOWNLOAD_DELAY", 2)
AUTOTHROTTLE_ENABLED = extra_settings.get("AUTOTHROTTLE_ENABLED", True)
AUTOTHROTTLE_START_DELAY = extra_settings.get("AUTOTHROTTLE_START_DELAY", 2)
AUTOTHROTTLE_MAX_DELAY = extra_settings.get("AUTOTHROTTLE_MAX_DELAY", 10)
AUTOTHROTTLE_TARGET_CONCURRENCY = extra_settings.get(
    "AUTOTHROTTLE_TARGET_CONCURRENCY", 1.0
)

# Retry on common temporary errors
RETRY_ENABLED = extra_settings.get("RETRY_ENABLED", True)
RETRY_TIMES = extra_settings.get("RETRY_TIMES", 3)
RETRY_HTTP_CODES = extra_settings.get("RETRY_HTTP_CODES", [429, 503])

# ----------------------------------------------------------------------
# Anti‑blocking middlewares
# ----------------------------------------------------------------------
DOWNLOADER_MIDDLEWARES = {
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
    "scrapy_user_agents.middlewares.RandomUserAgentMiddleware": 400,
    "scrapy_rotating_proxies.middlewares.RotatingProxyMiddleware": 610,
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": 550,
}

# Environment‑driven rotating proxy list (comma‑separated)
PROXY_LIST = os.getenv("PROXY_LIST", "")
ROTATING_PROXY_LIST = (
    [p.strip() for p in PROXY_LIST.split(",")] if PROXY_LIST else []
)

# ----------------------------------------------------------------------
# Item pipelines
# ----------------------------------------------------------------------
ITEM_PIPELINES = {
    "angalia.pipelines.ValidationPipeline": 100,
    "angalia.pipelines.DeduplicationPipeline": 200,
    "angalia.pipelines.SQLiteStorePipeline": 300,
    "angalia.pipelines.DiffPipeline": 400,
}

# ----------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(levelname)s %(asctime)s %(name)s %(message)s"
LOG_STDOUT = True
STRUCTLOG_LOGGING = True

# ----------------------------------------------------------------------
# Celery configuration (used by tasks)
# ----------------------------------------------------------------------
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.getenv(
    "CELERY_RESULT_BACKEND", "redis://redis:6379/1"
)
