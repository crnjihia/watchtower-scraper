import datetime
import scrapy
import yaml
from pathlib import Path
from ..items import ProductItem


class JumiaSpider(scrapy.Spider):
    name = "jumia"
    allowed_domains = ["jumia.co.ke"]
    custom_settings = {
        "DOWNLOAD_DELAY": 2,
        "AUTOTHROTTLE_ENABLED": True,
        "ROBOTSTXT_OBEY": True,
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 3,
    }

    def start_requests(self):
        """Load watchlist URLs from config/watchlist.yaml."""
        watchlist_path = Path(__file__).parents[2] / "config" / "watchlist.yaml"
        with open(watchlist_path, "r", encoding="utf-8") as f:
            watchlist = yaml.safe_load(f) or {}
        for url in watchlist.get("jumia", []):
            yield scrapy.Request(url, callback=self.parse_product)

    def parse_product(self, response):
        try:
            source = "jumia"
            external_id = response.url.split("/")[-1]
            name = response.css("h1.-fs20.-pts.-pbxs::text").get(""").strip()
            price_raw = response.css("span.-b.-ltr.-tal.-prc::text").get()
            price = float(
                price_raw.replace("KSh", "").replace(",", "").strip()
            )
            currency = "KES"
            in_stock = bool(
                response.css("span.-fs14.-p.-b.-trc::text").re_first(r"In stock")
            )
            rating_raw = response.css("span.-fs12.-pts::attr(title)").re_first(
                r"(\d\.\d) out of 5"
            )
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
            self.logger.error(f"Jumia parse error {response.url}: {exc}")
