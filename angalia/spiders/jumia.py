import re
from pathlib import Path

import scrapy
import structlog
import yaml

from ..items import ProductItem, utc_now

logger = structlog.get_logger(__name__)


class JumiaSpider(scrapy.Spider):
    name = "jumia"
    allowed_domains = ["jumia.co.ke", "www.jumia.co.ke"]

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
                urls = watchlist.get("jumia", [])
            except Exception as exc:
                self.logger.error(f"Failed to read watchlist.yaml: {exc}")

        if not urls:
            urls = [
                "https://www.jumia.co.ke/p/phone-iphone-13-pro-max-512gb-blue-5555555",
            ]

        for url in urls:
            yield scrapy.Request(url, callback=self.parse_product)

    def parse_product(self, response):
        """Extract product details from a Jumia product page."""
        try:
            source = "jumia"
            url_clean = response.url.split("?")[0].rstrip("/")
            external_id = url_clean.split("/")[-1]
            if not external_id:
                external_id = str(hash(response.url))

            name = (
                response.xpath("//h1//text()").get(default="")
                or response.css("h1.title::text, h1::text, [class*='-fs20']::text").get(default="")
            ).strip()

            # Price parsing
            price_raw = (
                response.xpath("//*[contains(@class, '-prc')]//text()").get()
                or response.css("span.price::text, div.-prc::text").get()
            )
            price = 0.0
            if price_raw:
                digits = re.sub(r"[^\d.]", "", price_raw.replace(",", ""))
                try:
                    price = float(digits)
                except ValueError:
                    price = 0.0

            currency = "KES"

            # In stock check
            stock_text = (
                response.xpath("//*[contains(@class, '-trc')]//text()").get()
                or response.css("div.stock::text").get(default="")
            )
            is_out_of_stock = bool(re.search(r"(?i)out of stock", stock_text))
            in_stock = not is_out_of_stock

            # Rating parsing
            rating = None
            rating_text = (
                response.xpath("//*[contains(@title, 'out of')]/@title").get()
                or response.css("div.stars ::text, [title*='out of']::attr(title)").get(default="")
            )
            rating_match = re.search(r"(\d+(?:\.\d+)?)", rating_text)
            if rating_match:
                try:
                    rating = float(rating_match.group(1))
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
            self.logger.error("Failed parsing Jumia product", url=response.url, error=str(exc))
