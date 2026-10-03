import datetime

import scrapy
import structlog

from ..items import JobItem, utc_now

logger = structlog.get_logger(__name__)


class FuzuSpider(scrapy.Spider):
    name = "fuzu"
    allowed_domains = ["fuzu.com", "www.fuzu.com"]
    start_urls = ["https://www.fuzu.com/jobs"]

    custom_settings = {
        "DOWNLOAD_DELAY": 2,
        "AUTOTHROTTLE_ENABLED": True,
        "ROBOTSTXT_OBEY": True,
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 3,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
    }

    def parse(self, response):
        """Parse job listing cards and pagination."""
        job_links = response.css(
            "article.job-card a::attr(href), a.job-card::attr(href), a[href*='/job/']::attr(href), a[href*='/jobs/']::attr(href)"
        ).getall()

        seen_links = set()
        for link in job_links:
            clean_link = link.strip()
            if clean_link and clean_link not in seen_links:
                seen_links.add(clean_link)
                yield response.follow(clean_link, callback=self.parse_job)

        next_page = response.css(
            "a[rel='next']::attr(href), a.pagination-next::attr(href), ul.pagination li.next a::attr(href)"
        ).get()
        if next_page:
            yield response.follow(next_page.strip(), callback=self.parse)

    def parse_job(self, response):
        """Extract job details from the Fuzu detail page."""
        try:
            source = "fuzu"
            url_path = response.url.split("?")[0].rstrip("/")
            external_id = url_path.split("/")[-1]
            if not external_id:
                external_id = str(hash(response.url))

            title = (
                response.css("h1.title::text, h1.job-title::text, h1::text")
                .get(default="")
                .strip()
            )
            company = (
                response.css("a.company::text, div.company-name::text, span.company::text")
                .get(default="")
                .strip()
            )
            location = (
                response.css("span.location::text, div.location::text")
                .get(default="")
                .strip()
                or None
            )
            job_type = (
                response.css("span.type::text, span.job-type::text")
                .get(default="")
                .strip()
                or None
            )
            salary = (
                response.css("span.salary::text, div.salary::text")
                .get(default="")
                .strip()
                or None
            )

            posted_raw = response.css("time::attr(datetime)").get()
            posted_at = None
            if posted_raw:
                try:
                    posted_at = datetime.datetime.fromisoformat(posted_raw.strip())
                except ValueError:
                    posted_at = None

            description_parts = response.css(
                "section.description ::text, div.description ::text, div.job-body ::text"
            ).getall()
            description_snippet = " ".join(
                [s.strip() for s in description_parts if s.strip()]
            )[:300] or None

            item = JobItem(
                source=source,
                external_id=external_id,
                url=response.url,
                scraped_at=utc_now(),
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
            self.logger.error("Failed parsing Fuzu job", url=response.url, error=str(exc))
