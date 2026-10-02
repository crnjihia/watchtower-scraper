import datetime
import scrapy
from ..items import JobItem


class BrighterMondaySpider(scrapy.Spider):
    name = "brighter_monday"
    allowed_domains = ["brightermonday.com"]
    start_urls = ["https://www.brightermonday.com/jobs"]

    custom_settings = {
        "DOWNLOAD_DELAY": 2,
        "AUTOTHROTTLE_ENABLED": True,
        "ROBOTSTXT_OBEY": True,
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 3,
    }

    def parse(self, response):
        """
        The main job listing page contains a list of job cards.
        Each card links to a detail page we need to follow.
        """
        job_links = response.css("a.job-card::attr(href)").getall()
        for link in job_links:
            yield response.follow(link, callback=self.parse_job)

        # Pagination handling – next page button.
        next_page = response.css("a.pagination-next::attr(href)").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

    def parse_job(self, response):
        """Extract job details from the job‑detail page."""
        try:
            source = "brightermonday"
            external_id = response.url.split("/")[-1]
            title = response.css("h1.job-title::text").get(default="").strip()
            company = response.css("div.company-name a::text").get(default="").strip()
            location = response.css("span.location::text").get()
            job_type = response.css("span.job-type::text").get()
            salary = response.css("span.salary::text").get()
            posted_raw = response.css("time.posted::attr(datetime)").get()
            posted_at = (
                datetime.datetime.fromisoformat(posted_raw) if posted_raw else None
            )
            description_snippet = response.css("div.description ::text").getall()
            description_snippet = " ".join(
                [s.strip() for s in description_snippet if s.strip()]
            )[:200]

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
            self.logger.error(f"Failed parsing job page {response.url}: {exc}")
