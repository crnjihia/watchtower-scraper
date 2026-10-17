"""Spiders module for Kenyan job boards and e-commerce platforms."""

from watchtower.spiders.base import BaseSpider
from watchtower.spiders.brighter_monday import BrighterMondaySpider
from watchtower.spiders.fuzu import FuzuSpider
from watchtower.spiders.jumia import JumiaSpider
from watchtower.spiders.kilimall import KilimallSpider
from watchtower.spiders.my_job_mag import MyJobMagSpider

__all__ = [
    "BaseSpider",
    "BrighterMondaySpider",
    "FuzuSpider",
    "MyJobMagSpider",
    "JumiaSpider",
    "KilimallSpider",
]
