import datetime
import scrapy
import yaml
from pathlib import Path
from ..items import ProductItem


class KilimallSpider(scrapy.Spider):
    name = "kilimall"
    allowed_domains = ["kilimall.co.ke"]
    custom_settings = {
        "DOWNLOAD_DELAY": 2,
        "AUTOTHROTTLE_ENABLED": True,
        "ROBOTSTXT_OBEY": True,
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 3,
    }

    def start_requests(self):
        watchlist_path = Path(__file__).parents[2] / "config" / "watchlist.yaml"
        with open(watchlist_path, "r", encoding="utf-8") as f:
            watchlist = yaml.safe_load(f) or {}
        for url in watchlist.get("kilimall", []):
            yield scrapy.Request(url, callback=self.parse_product)

    def parse_product(self, response):
        try:
            source = "kilimall"
            external_id = response.url.split("/")[-1]
            name = response.css("h1.prod-title::text").get(""").strip()
            price_raw = response.css("span.curr-price::text").get()
            price = float(price_raw.replace("KSh", "").replace(",", "").strip())
            currency = "KES"
            stock_text = response.css("div.availability span::text").re_first(
                r"In stock|Out of stock"
            )
            in_stock = stock_text == "In stock"
            rating_raw = response.css("div.rating span::attr(data-rating)").get()
            rating = float(rating_raw) if rating_raw else None

            item = ProductItem(
                source=source,
                external_id=external_id,
                url=response.url,
                scraped_at=datetime.datetime.utcnow(),
                name=name,
                price=price,
                currency=currency,
                in_stock=in_stock,
                rating=rating,
            )
            yield item
        except Exception as exc:
            self.logger.error(f"Kilimall parse error {response.url}: {exc}")
