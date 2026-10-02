import datetime
import scrapy
from ..items import JobItem


class FuzuSpider(scrapy.Spider):
    name = "fuzu"
    allowed_domains = ["fuzu.com"]
    start_urls = ["https://www.fuzu.com/jobs"]

    custom_settings = {
        "DOWNLOAD_DELAY": 2,
        "AUTOTHROTTLE_ENABLED": True,
        "ROBOTSTXT_OBEY": True,
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 3,
    }

    def parse(self, response):
        job_cards = response.css("article.job-card")
        for card in job_cards:
            link = card.css("a::attr(href)").get()
            if link:
                yield response.follow(link, callback=self.parse_job)

        # Next page
        next_page = response.css("a[rel='next']::attr(href)").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

    def parse_job(self, response):
        try:
            source = "fuzu"
            external_id = response.url.split("/")[-1]
            title = response.css("h1.title::text").get("").strip()
            company = response.css("a.company::text").get("").strip()
            location = response.css("span.location::text").get()
            job_type = response.css("span.type::text").get()
            salary = response.css("span.salary::text").get()
            posted_raw = response.css("time::attr(datetime)").get()
            posted_at = (
                datetime.datetime.fromisoformat(posted_raw) if posted_raw else None
            )
            description = response.css("section.description ::text").getall()
            description_snippet = " ".join([s.strip() for s in description if s.strip()])[:200]

            item = JobItem(
                source=source,
                external_id=external_id,
                url=response.url,
                scraped_at=datetime.datetime.utcnow(),
                title=title,
                company=company,
                location=location,
                job_type=job_type,
                salary=salary,
                posted_at=posted_at,
                description_snippet=description_snippet,
            )
            yield item
        except Exception as exc:
            self.logger.error(f"Fuzu parse error on {response.url}: {exc}")
