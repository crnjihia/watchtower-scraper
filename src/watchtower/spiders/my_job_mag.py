"""MyJobMag job board spider for Kenya."""

from typing import Any, Dict, Generator

from scrapy.http import Response

from watchtower.logging import get_logger
from watchtower.spiders.base import BaseSpider

logger = get_logger(__name__)


class MyJobMagSpider(BaseSpider):
    """Spider for crawling job postings from MyJobMag Kenya."""

    name = "my_job_mag"
    allowed_domains = ["myjobmag.co.ke", "www.myjobmag.co.ke"]
    start_urls = ["https://www.myjobmag.co.ke/jobs"]

    def parse(self, response: Response) -> Generator[Any, None, None]:
        """Parse job listings and follow links to detail pages."""
        job_links = response.css(
            "div.job-listing a.title::attr(href), div.job-info a::attr(href), li.job-list-li a::attr(href), a[href*='/job/']::attr(href), a[href*='/jobs/']::attr(href)"
        ).getall()

        seen_links = set()
        for link in job_links:
            clean_link = link.strip()
            if "/page/" in clean_link or "/company/" in clean_link:
                continue
            if clean_link and clean_link not in seen_links:
                seen_links.add(clean_link)
                yield response.follow(clean_link, callback=self.parse_job)

        next_page = response.css(
            "ul.pagination li.next a::attr(href), a[rel='next']::attr(href), a.next-page::attr(href)"
        ).get()
        if next_page:
            yield response.follow(next_page.strip(), callback=self.parse)

    def parse_job(self, response: Response) -> Generator[Dict[str, Any], None, None]:
        """Extract canonical job details from MyJobMag detail page."""
        try:
            url_path = response.url.split("?")[0].rstrip("/")
            external_id = url_path.split("/")[-1] or str(hash(response.url))

            title = (
                response.css("h1.job-title::text, h1.title::text, h1::text")
                .get(default="")
                .strip()
            )
            if not title:
                logger.warning("my_job_mag_missing_title", url=response.url)
                title = "Untitled Job"

            company = (
                response.css("div.company a::text, a.company::text, span.company::text, li.com-name a::text")
                .get(default="")
                .strip()
            )
            if not company:
                company = response.xpath("//a[contains(@href, '/company/')]//text()").get(default="").strip()
            if not company:
                company = "Confidential Employer"

            location = (
                response.css("span.location::text, div.location::text, li.location::text")
                .get(default="")
                .strip()
                or None
            )

            job_type = (
                response.css("span.contract::text, span.job-type::text, li.type::text")
                .get(default="")
                .strip()
                or None
            )

            salary_raw = (
                response.css("span.salary::text, div.salary::text, li.salary::text")
                .get(default="")
                .strip()
            )

            posted_at = (
                response.css("time.posted::attr(datetime), time::attr(datetime)").get()
                or response.css("time.posted::text, time::text").get(default="")
            )

            yield self.build_item(
                site="my_job_mag",
                external_id=external_id,
                url=response.url,
                title=title,
                company=company,
                price_kes=None,
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
            logger.warning("my_job_mag_parse_job_error", url=response.url, error=str(e))
