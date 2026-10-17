"""Scrapy Item Pipelines for normalization, change detection, and persistence."""

from watchtower.pipelines.change_detect import ChangeDetectionPipeline, detect_item_change
from watchtower.pipelines.normalize import NormalizePipeline
from watchtower.pipelines.persist import PersistPipeline

__all__ = [
    "NormalizePipeline",
    "ChangeDetectionPipeline",
    "PersistPipeline",
    "detect_item_change",
]
