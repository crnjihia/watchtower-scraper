"""Jumia Kenya e-commerce spider."""

from pathlib import Path
from typing import Any, Dict, Generator

import scrapy
import yaml
from scrapy.http import Response

from watchtower.logging import get_logger
from watchtower.spiders.base import BaseSpider

logger = get_logger(__name__)


class JumiaSpider(BaseSpider):
    """Spider for crawling product prices and listings from Jumia Kenya."""

    name = "jumia"
    allowed_domains = ["jumia.co.ke", "www.jumia.co.ke"]
    start_urls = [
        "https://www.jumia.co.ke/smartphones/",
        "https://www.jumia.co.ke/laptops/",
    ]

    def start_requests(self) -> Generator[scrapy.Request, None, None]:
        """Load target watchlist URLs from config/watchlist.yaml if available, else start_urls."""
        watchlist_file = Path("config/watchlist.yaml")
        urls = []
        if watchlist_file.is_file():
            try:
                with open(watchlist_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                    urls = data.get("jumia", [])
            except Exception as e:
                logger.warning("jumia_failed_reading_watchlist", error=str(e))

        if not urls:
            urls = self.start_urls

        for url in urls:
            # If it's a direct product page
            if "/p/" in url or url.endswith(".html"):
                yield scrapy.Request(url, callback=self.parse_product)
            else:
                yield scrapy.Request(url, callback=self.parse)

    def parse(self, response: Response) -> Generator[Any, None, None]:
        """Extract product links from catalog/listing page."""
        product_links = response.css(
            "article.prd a.core::attr(href), a[href*='.html']::attr(href), a[href*='/p/']::attr(href)"
        ).getall()

        seen_links = set()
        for link in product_links:
            clean = link.strip()
            if clean and clean not in seen_links:
                seen_links.add(clean)
                yield response.follow(clean, callback=self.parse_product)

        next_page = response.css("a[aria-label='Next Page']::attr(href), a.pg::attr(href)").get()
        if next_page:
            yield response.follow(next_page.strip(), callback=self.parse)

    def parse_product(self, response: Response) -> Generator[Dict[str, Any], None, None]:
        """Extract canonical product details from Jumia product page."""
        try:
            url_clean = response.url.split("?")[0].rstrip("/")
            external_id = url_clean.split("/")[-1] or str(hash(response.url))

            title = (
                response.xpath("//h1//text()").get(default="")
                or response.css("h1.title::text, h1::text, [class*='-fs20']::text").get(default="")
            ).strip()
            if not title:
                logger.warning("jumia_missing_title", url=response.url)
                title = "Untitled Product"

            price_raw = (
                response.xpath("//*[contains(@class, '-prc')]//text()").get()
                or response.css("span.price::text, div.-prc::text, span.-b::text").get()
            )

            seller = (
                response.css("div.seller-name::text, a.seller-link::text, p.-m::text")
                .get(default="")
                .strip()
                or "Jumia Official"
            )

            stock = (
                response.css("[class*='-trc']::text, span.stock::text")
                .get(default="")
                .strip()
            )

            rating = (
                response.css("div.stars span::text, span.stars::text")
                .get(default="")
                .strip()
            )

            category = (
                response.css("div.brc a::text, div.breadcrumbs a::text")
                .get(default="")
                .strip()
                or "E-Commerce"
            )

            yield self.build_item(
                site="jumia",
                external_id=external_id,
                url=response.url,
                title=title,
                company=seller,  # Seller representation
                price_kes=price_raw,  # Normalized to float in NormalizePipeline
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
            logger.warning("jumia_parse_product_error", url=response.url, error=str(e))
