"""Scrapy settings for Watchtower Scraper monitoring system."""

import os
from pathlib import Path

BOT_NAME = "watchtower"

SPIDER_MODULES = ["watchtower.spiders"]
NEWSPIDER_MODULE = "watchtower.spiders"

# Obey robots.txt rules strictly for ethical crawling
ROBOTSTXT_OBEY = True

# Polite crawling defaults
CONCURRENT_REQUESTS = 1
CONCURRENT_REQUESTS_PER_DOMAIN = 1

DOWNLOAD_DELAY = 2.0
RANDOMIZE_DOWNLOAD_DELAY = True

# AutoThrottle extension for dynamic politeness adjustment
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 2.0
AUTOTHROTTLE_MAX_DELAY = 10.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
AUTOTHROTTLE_DEBUG = False

# Twisted and Scrapy modern settings
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"

# Pipeline execution sequence
ITEM_PIPELINES = {
    "watchtower.pipelines.normalize.NormalizePipeline": 100,
    "watchtower.pipelines.change_detect.ChangeDetectPipeline": 200,
    "watchtower.pipelines.persist.PersistPipeline": 300,
}

# Downloader middlewares
DOWNLOADER_MIDDLEWARES = {
    "watchtower.spiders.base.RotateUserAgentMiddleware": 400,
    "watchtower.spiders.base.HttpProxyMiddleware": 410,
}

# Log level
LOG_LEVEL = os.getenv("SCRAPY_LOG_LEVEL", "INFO")
