"""Kilimall Kenya e-commerce spider."""

from pathlib import Path
from typing import Any, Dict, Generator

import scrapy
import yaml
from scrapy.http import Response

from watchtower.logging import get_logger
from watchtower.spiders.base import BaseSpider

logger = get_logger(__name__)


class KilimallSpider(BaseSpider):
    """Spider for crawling product prices and listings from Kilimall Kenya."""

    name = "kilimall"
    allowed_domains = ["kilimall.co.ke", "www.kilimall.co.ke"]
    start_urls = [
        "https://www.kilimall.co.ke/new/commoditysearch?c=1067",
    ]

    def start_requests(self) -> Generator[scrapy.Request, None, None]:
        """Load target watchlist URLs from config/watchlist.yaml if available, else start_urls."""
        watchlist_file = Path("config/watchlist.yaml")
        urls = []
        if watchlist_file.is_file():
            try:
                with open(watchlist_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                    urls = data.get("kilimall", [])
            except Exception as e:
                logger.warning("kilimall_failed_reading_watchlist", error=str(e))

        if not urls:
            urls = self.start_urls

        for url in urls:
            if "/p/" in url or "/item/" in url:
                yield scrapy.Request(url, callback=self.parse_product)
            else:
                yield scrapy.Request(url, callback=self.parse)

    def parse(self, response: Response) -> Generator[Any, None, None]:
        """Extract product links from catalog page."""
        product_links = response.css(
            "div.goods-list a::attr(href), a[href*='/item/']::attr(href), a[href*='/p/']::attr(href), div.product a::attr(href)"
        ).getall()

        seen_links = set()
        for link in product_links:
            clean = link.strip()
            if clean and clean not in seen_links:
                seen_links.add(clean)
                yield response.follow(clean, callback=self.parse_product)

        next_page = response.css("a.next::attr(href), a[rel='next']::attr(href)").get()
        if next_page:
            yield response.follow(next_page.strip(), callback=self.parse)

    def parse_product(self, response: Response) -> Generator[Dict[str, Any], None, None]:
        """Extract canonical product details from Kilimall product page."""
        try:
            url_clean = response.url.split("?")[0].rstrip("/")
            external_id = url_clean.split("/")[-1] or str(hash(response.url))

            title = (
                response.css("h1.prod-title::text, h1.product-title::text, h1::text")
                .get(default="")
                .strip()
            )
            if not title:
                logger.warning("kilimall_missing_title", url=response.url)
                title = "Untitled Product"

            price_raw = response.css(
                "span.curr-price::text, span.price::text, div.price-box span::text"
            ).get()

            seller = (
                response.css("div.shop-name a::text, div.seller a::text, span.shop-name::text")
                .get(default="")
                .strip()
                or "Kilimall Official"
            )

            stock = (
                response.css("div.availability span::text, span.stock::text")
                .get(default="")
                .strip()
            )

            rating = (
                response.css("div.rating span::text, [data-rating]::text")
                .get(default="")
                .strip()
            )

            category = (
                response.css("div.breadcrumb a::text, span.category::text")
                .get(default="")
                .strip()
                or "E-Commerce"
            )

            yield self.build_item(
                site="kilimall",
                external_id=external_id,
                url=response.url,
                title=title,
                company=seller,
                price_kes=price_raw,
                currency="KES",
                location="Kenya",
                posted_at=None,
                category=category,
                raw={
                    "stock": stock,
                    "rating": rating,
                    "price_raw": price_raw,
                },
            )
        except Exception as e:
            logger.warning("kilimall_parse_product_error", url=response.url, error=str(e))
