"""Fuzu job board spider for Kenya."""

from typing import Any, Dict, Generator

from scrapy.http import Response

from watchtower.logging import get_logger
from watchtower.spiders.base import BaseSpider

logger = get_logger(__name__)


class FuzuSpider(BaseSpider):
    """Spider for crawling job postings from Fuzu Kenya."""

    name = "fuzu"
    allowed_domains = ["fuzu.com", "www.fuzu.com"]
    start_urls = ["https://www.fuzu.com/kenya/jobs", "https://www.fuzu.com/jobs"]

    def parse(self, response: Response) -> Generator[Any, None, None]:
        """Parse job listings and follow links to detail pages."""
        job_links = response.css(
            "article.job-card a::attr(href), a[href*='/jobs/']::attr(href), div.job-card a::attr(href)"
        ).getall()

        seen_links = set()
        for link in job_links:
            clean_link = link.strip()
            if not clean_link or "/companies/" in clean_link:
                continue
            if clean_link not in seen_links:
                seen_links.add(clean_link)
                yield response.follow(clean_link, callback=self.parse_job)

        next_page = response.css("a[rel='next']::attr(href), a.pagination-next::attr(href)").get()
        if next_page:
            yield response.follow(next_page.strip(), callback=self.parse)

    def parse_job(self, response: Response) -> Generator[Dict[str, Any], None, None]:
        """Extract canonical job details from Fuzu detail page."""
        try:
            url_path = response.url.split("?")[0].rstrip("/")
            external_id = url_path.split("/")[-1] or str(hash(response.url))

            title = (
                response.css("h1.title::text, h1::text, div.job-container h1::text")
                .get(default="")
                .strip()
            )
            if not title:
                logger.warning("fuzu_missing_title", url=response.url)
                title = "Untitled Job"

            company = (
                response.css(
                    "div.employer-info a.company::text, a.company::text, span.company::text, div.company-title::text"
                )
                .get(default="")
                .strip()
            )
            if not company:
                company = response.xpath("//a[contains(@href, '/companies/')]//text()").get(default="").strip()
            if not company:
                company = "Confidential Employer"

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

            salary_raw = (
                response.css("span.salary::text, div.salary::text")
                .get(default="")
                .strip()
            )

            posted_at = (
                response.css("time::attr(datetime)").get()
                or response.css("time::text").get(default="")
            )

            yield self.build_item(
                site="fuzu",
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
            logger.warning("fuzu_parse_job_error", url=response.url, error=str(e))
