import datetime

import scrapy
import structlog

from ..items import JobItem, utc_now

logger = structlog.get_logger(__name__)


class MyJobMagSpider(scrapy.Spider):
    name = "myjobmag"
    allowed_domains = ["myjobmag.co.ke", "www.myjobmag.co.ke"]
    start_urls = ["https://www.myjobmag.co.ke/jobs"]

    custom_settings = {
        "DOWNLOAD_DELAY": 2,
        "AUTOTHROTTLE_ENABLED": True,
        "ROBOTSTXT_OBEY": True,
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 3,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
    }

    def parse(self, response):
        """Parse job listings and follow links to detail pages."""
        job_links = response.css(
            "div.job-listing a.title::attr(href), div.job-info a::attr(href), li.job-list-li a::attr(href), a[href*='/job/']::attr(href), a[href*='/jobs/']::attr(href)"
        ).getall()

        seen_links = set()
        for link in job_links:
            clean_link = link.strip()
            if "/page/" in clean_link:
                continue
            if clean_link and clean_link not in seen_links:
                seen_links.add(clean_link)
                yield response.follow(clean_link, callback=self.parse_job)

        next_page = response.css(
            "ul.pagination li.next a::attr(href), a[rel='next']::attr(href), a.next-page::attr(href)"
        ).get()
        if next_page:
            yield response.follow(next_page.strip(), callback=self.parse)

    def parse_job(self, response):
        """Extract job details from the MyJobMag detail page."""
        try:
            source = "myjobmag"
            url_path = response.url.split("?")[0].rstrip("/")
            external_id = url_path.split("/")[-1]
            if not external_id:
                external_id = str(hash(response.url))

            title = (
                response.css("h1.job-title::text, h1.title::text, h1::text")
                .get(default="")
                .strip()
            )
            company = (
                response.css("div.company a::text, span.company a::text, a.company::text, a[href*='/jobs-at/']::text")
                .get(default="")
                .strip()
            )
            if not company and " at " in title:
                company = title.split(" at ")[-1].strip()
            if not company:
                company = "Confidential Employer"

            location = (
                response.css("span.location::text, div.location::text")
                .get(default="")
                .strip()
                or None
            )
            job_type = (
                response.css("span.contract::text, span.job-type::text")
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

            posted_raw = response.css(
                "time.posted::attr(datetime), time::attr(datetime)"
            ).get()
            posted_at = None
            if posted_raw:
                try:
                    posted_at = datetime.datetime.fromisoformat(posted_raw.strip())
                except ValueError:
                    posted_at = None

            description_parts = response.css(
                "section.job-description ::text, div.job-description ::text, div.job-details ::text"
            ).getall()
            description_snippet = " ".join(
                [p.strip() for p in description_parts if p.strip()]
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
            self.logger.error("Failed parsing MyJobMag job", url=response.url, error=str(exc))
