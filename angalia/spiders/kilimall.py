import re
from pathlib import Path

import scrapy
import structlog
import yaml

from ..items import ProductItem, utc_now

logger = structlog.get_logger(__name__)


class KilimallSpider(scrapy.Spider):
    name = "kilimall"
    allowed_domains = ["kilimall.co.ke", "www.kilimall.co.ke"]

    custom_settings = {
        "DOWNLOAD_DELAY": 2,
        "AUTOTHROTTLE_ENABLED": True,
        "ROBOTSTXT_OBEY": True,
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 3,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
    }

    def start_requests(self):
        """Load watchlist URLs from config/watchlist.yaml."""
        watchlist_path = Path(__file__).resolve().parents[2] / "config" / "watchlist.yaml"
        urls = []
        if watchlist_path.is_file():
            try:
                with open(watchlist_path, "r", encoding="utf-8") as f:
                    watchlist = yaml.safe_load(f) or {}
                urls = watchlist.get("kilimall", [])
            except Exception as exc:
                self.logger.error(f"Failed to read watchlist.yaml: {exc}")

        if not urls:
            urls = [
                "https://www.kilimall.co.ke/p/iphone-13-pro-max-512gb-blue-111111",
            ]

        for url in urls:
            yield scrapy.Request(url, callback=self.parse_product)

    def parse_product(self, response):
        """Extract product details from a Kilimall product page."""
        try:
            source = "kilimall"
            url_clean = response.url.split("?")[0].rstrip("/")
            external_id = url_clean.split("/")[-1]
            if not external_id:
                external_id = str(hash(response.url))

            name = (
                response.css("h1.prod-title::text, h1.product-title::text, h1::text")
                .get(default="")
                .strip()
            )

            # Price parsing
            price_raw = response.css(
                "span.curr-price::text, span.price::text, div.price-box span::text"
            ).get()
            price = 0.0
            if price_raw:
                digits = re.sub(r"[^\d.]", "", price_raw.replace(",", ""))
                try:
                    price = float(digits)
                except ValueError:
                    price = 0.0

            currency = "KES"

            # In stock check
            stock_text = response.css(
                "div.availability span::text, span.stock::text, div.stock-status::text"
            ).get(default="")
            is_out_of_stock = bool(re.search(r"(?i)out of stock", stock_text))
            in_stock = not is_out_of_stock

            # Rating parsing
            rating = None
            rating_raw = response.css(
                "div.rating span::attr(data-rating), span.rating-score::text, span.score::text"
            ).get()
            if rating_raw:
                digits = re.sub(r"[^\d.]", "", rating_raw)
                try:
                    rating = float(digits)
                except ValueError:
                    rating = None

            item = ProductItem(
                source=source,
                external_id=external_id,
                url=response.url,
                scraped_at=utc_now(),
                name=name,
                price=price,
                currency=currency,
                in_stock=in_stock,
                rating=rating,
            )
            yield item
        except Exception as exc:
            self.logger.error("Failed parsing Kilimall product", url=response.url, error=str(exc))
