"""BrighterMonday job board spider for Kenya."""

from typing import Any, Dict, Generator

from scrapy.http import Response

from watchtower.logging import get_logger
from watchtower.spiders.base import BaseSpider

logger = get_logger(__name__)


class BrighterMondaySpider(BaseSpider):
    """Spider for crawling job postings from BrighterMonday Kenya."""

    name = "brighter_monday"
    allowed_domains = [
        "brightermonday.com",
        "brightermonday.co.ke",
        "www.brightermonday.co.ke",
        "www.brightermonday.com",
    ]
    start_urls = [
        "https://www.brightermonday.co.ke/jobs",
        "https://www.brightermonday.com/jobs",
    ]

    def parse(self, response: Response) -> Generator[Any, None, None]:
        """Extract job listing links and follow pagination."""
        job_links = response.css(
            "a[href*='/listings/']::attr(href), a.job-card::attr(href), div.job-card a::attr(href), a[href*='/jobs/']::attr(href)"
        ).getall()

        seen_links = set()
        for link in job_links:
            clean_link = link.strip()
            if not clean_link or "/employer/" in clean_link or "/company/" in clean_link:
                continue
            if clean_link not in seen_links:
                seen_links.add(clean_link)
                yield response.follow(clean_link, callback=self.parse_job)

        next_page = response.css(
            "a.pagination-next::attr(href), a[rel='next']::attr(href), li.next a::attr(href)"
        ).get()
        if next_page:
            yield response.follow(next_page.strip(), callback=self.parse)

    def parse_job(self, response: Response) -> Generator[Dict[str, Any], None, None]:
        """Extract canonical job listing details from job page."""
        try:
            url_path = response.url.split("?")[0].rstrip("/")
            external_id = url_path.split("/")[-1] or str(hash(response.url))

            title = (
                response.css("[data-cy='title-job']::text, h1.job-title::text, h1.title::text, h1::text")
                .get(default="")
                .strip()
            )
            if not title:
                logger.warning("brighter_monday_missing_title", url=response.url)
                title = "Untitled Job"

            company = (
                response.css(
                    "div.company-name a::text, a.company::text, span.company::text, h2.text-base::text, a[href*='/companies/']::text, a[href*='/employer/']::text"
                )
                .get(default="")
                .strip()
            )
            if not company:
                company = response.xpath("//h1/following::h2[1]//text()").get(default="").strip()
            if not company:
                company = "Confidential Employer"

            location = (
                response.css(
                    "span.location::text, div.location::text, span[data-testid='location']::text"
                )
                .get(default="")
                .strip()
                or None
            )

            job_type = (
                response.css(
                    "span.job-type::text, span.contract::text, span[data-testid='job-type']::text"
                )
                .get(default="")
                .strip()
                or None
            )

            salary_raw = (
                response.css("span.salary::text, div.salary::text, span[data-testid='salary']::text")
                .get(default="")
                .strip()
            )

            posted_at = (
                response.css("time.posted::attr(datetime), time::attr(datetime)").get()
                or response.css("time.posted::text, time::text").get(default="")
            )

            yield self.build_item(
                site="brighter_monday",
                external_id=external_id,
                url=response.url,
                title=title,
                company=company,
                price_kes=None,  # Price is parsed/normalized in pipeline if present in salary
                currency="KES",
                location=location,
                posted_at=posted_at,
                category="Job",
                raw={
                    "job_type": job_type,
                    "salary_raw": salary_raw,
                },
            )
        except Exception as e:
            logger.warning("brighter_monday_parse_job_error", url=response.url, error=str(e))
