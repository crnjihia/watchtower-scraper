import datetime

import scrapy
import structlog

from ..items import JobItem, utc_now

logger = structlog.get_logger(__name__)


class BrighterMondaySpider(scrapy.Spider):
    name = "brighter_monday"
    allowed_domains = [
        "brightermonday.com",
        "brightermonday.co.ke",
        "www.brightermonday.co.ke",
        "www.brightermonday.com",
    ]
    start_urls = ["https://www.brightermonday.co.ke/jobs", "https://www.brightermonday.com/jobs"]


    custom_settings = {
        "DOWNLOAD_DELAY": 2,
        "AUTOTHROTTLE_ENABLED": True,
        "ROBOTSTXT_OBEY": True,
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 3,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
    }

    def parse(self, response):
        """Parse job listings and follow links to detail pages and pagination."""
        job_links = response.css(
            "a[href*='/listings/']::attr(href), a.job-card::attr(href), div.job-card a::attr(href)"
        ).getall()

        seen_links = set()
        for link in job_links:
            clean_link = link.strip()
            if not clean_link or "/employer/" in clean_link:
                continue
            if clean_link not in seen_links:
                seen_links.add(clean_link)
                yield response.follow(clean_link, callback=self.parse_job)

        next_page = response.css(
            "a.pagination-next::attr(href), a[rel='next']::attr(href), li.next a::attr(href)"
        ).get()
        if next_page:
            yield response.follow(next_page.strip(), callback=self.parse)

    def parse_job(self, response):
        """Extract job details from the job detail page."""
        try:
            source = "brightermonday"

            # Extract external ID from URL (e.g. /jobs/software-engineer-12345 or /listings/tax-manager-6q6d86)
            url_path = response.url.split("?")[0].rstrip("/")
            external_id = url_path.split("/")[-1]
            if not external_id:
                external_id = str(hash(response.url))

            title = (
                response.css("[data-cy='title-job']::text, h1.job-title::text, h1.title::text, h1::text")
                .get(default="")
                .strip()
            )
            company = (
                response.css(
                    "div.company-name a::text, a.company::text, span.company::text, h2.text-base::text, a[href*='/companies/']::text, a[href*='/employer/']::text, p[class*='text-sm'] a::text"
                )
                .get(default="")
                .strip()
            )
            if not company:
                company = response.xpath("//h1/following::h2[1]//text()").get(default="").strip()
            if not company:
                company = response.xpath(
                    "//a[contains(@href, '/companies/') or contains(@href, '/employer/')]//text()"
                ).get(default="").strip()
            if not company:
                company_parts = response.css("div.company-name ::text").getall()
                company = " ".join([p.strip() for p in company_parts if p.strip()])
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
                "div.description ::text, section.job-description ::text, div.job-body ::text"
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
            self.logger.error("Failed parsing BrighterMonday job", url=response.url, error=str(exc))
