import hashlib
from dataclasses import asdict, dataclass, field, fields
from datetime import UTC, datetime
from typing import Any


def utc_now() -> datetime:
    """Return naive UTC timestamp compatible with SQLite and standard datetime operations."""
    return datetime.now(UTC).replace(tzinfo=None)


def hash_fields(values: list[Any]) -> str:
    """Create a SHA-256 hash from a list of values."""
    concatenated = "|".join("" if v is None else str(v).strip() for v in values)
    return hashlib.sha256(concatenated.encode("utf-8")).hexdigest()


@dataclass
class AngaliaItem:
    """Base fields common to all items."""
    source: str
    external_id: str
    url: str
    scraped_at: datetime = field(default_factory=utc_now)
    content_hash: str = ""

    def __post_init__(self):
        if not self.content_hash:
            self.content_hash = self.compute_hash()

    def compute_hash(self) -> str:
        """Default hash based on source, external_id, url."""
        return hash_fields([self.source, self.external_id, self.url])

    def to_dict(self) -> dict[str, Any]:
        """Convert item to JSON-serializable dictionary."""
        data = asdict(self)
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        return data

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any):
        setattr(self, key, value)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def keys(self):
        return [f.name for f in fields(self)]

    def items(self):
        return [(f.name, getattr(self, f.name)) for f in fields(self)]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AngaliaItem":
        raise NotImplementedError


# Alias for Watchtower Scraper branding
WatchtowerItem = AngaliaItem


# ---- Job items ---------------------------------------------------------

@dataclass
class JobItem(AngaliaItem):
    title: str = ""
    company: str = ""
    location: str | None = None
    job_type: str | None = None
    salary: str | None = None
    posted_at: datetime | None = None
    description_snippet: str | None = None

    def compute_hash(self) -> str:
        """SHA-256 hash of identifying job fields."""
        return hash_fields([
            self.source,
            self.external_id,
            self.title,
            self.company,
            self.location,
            self.job_type,
            self.salary,
        ])

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JobItem":
        scraped = data.get("scraped_at")
        if isinstance(scraped, str):
            scraped = datetime.fromisoformat(scraped)
        elif not isinstance(scraped, datetime):
            scraped = utc_now()

        posted = data.get("posted_at")
        if isinstance(posted, str):
            posted = datetime.fromisoformat(posted)

        return cls(
            source=data.get("source", ""),
            external_id=str(data.get("external_id", "")),
            url=data.get("url", ""),
            scraped_at=scraped,
            content_hash=data.get("content_hash", ""),
            title=data.get("title", ""),
            company=data.get("company", ""),
            location=data.get("location"),
            job_type=data.get("job_type"),
            salary=data.get("salary"),
            posted_at=posted,
            description_snippet=data.get("description_snippet"),
        )


# ---- Product items -------------------------------------------------------

@dataclass
class ProductItem(AngaliaItem):
    name: str = ""
    price: float = 0.0
    currency: str = "KES"
    in_stock: bool = True
    rating: float | None = None

    def compute_hash(self) -> str:
        """SHA-256 hash of identifying product fields."""
        return hash_fields([
            self.source,
            self.external_id,
            self.name,
            str(self.price),
            str(self.in_stock),
        ])

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProductItem":
        scraped = data.get("scraped_at")
        if isinstance(scraped, str):
            scraped = datetime.fromisoformat(scraped)
        elif not isinstance(scraped, datetime):
            scraped = utc_now()

        raw_price = data.get("price", 0.0)
        try:
            price = float(raw_price)
        except (ValueError, TypeError):
            price = 0.0

        raw_rating = data.get("rating")
        try:
            rating = float(raw_rating) if raw_rating is not None else None
        except (ValueError, TypeError):
            rating = None

        return cls(
            source=data.get("source", ""),
            external_id=str(data.get("external_id", "")),
            url=data.get("url", ""),
            scraped_at=scraped,
            content_hash=data.get("content_hash", ""),
            name=data.get("name", ""),
            price=price,
            currency=data.get("currency", "KES"),
            in_stock=bool(data.get("in_stock", True)),
            rating=rating,
        )
