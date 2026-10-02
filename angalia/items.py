import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


def _hash_content(values: list[str]) -> str:
    """Create a SHA‑256 hash from a list of stringified values."""
    concatenated = "|".join(values)
    return hashlib.sha256(concatenated.encode()).hexdigest()


@dataclass
class AngaliaItem:
    """Base fields common to all items."""
    source: str
    external_id: str
    url: str
    scraped_at: datetime
    content_hash: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AngaliaItem":
        raise NotImplementedError


# ---- Job items ---------------------------------------------------------

@dataclass
class JobItem(AngaliaItem):
    title: str
    company: str
    location: Optional[str] = None
    job_type: Optional[str] = None
    salary: Optional[str] = None
    posted_at: Optional[datetime] = None
    description_snippet: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JobItem":
        required = ["source", "external_id", "url", "scraped_at"]
        for key in required:
            if key not in data:
                raise ValueError(f"Missing required field {key}")

        hash_fields = [data["source"], data["external_id"], data["url"]]
        content_hash = _hash_content(hash_fields)

        return cls(
            source=data["source"],
            external_id=data["external_id"],
            url=data["url"],
            scraped_at=data["scraped_at"],
            content_hash=content_hash,
            title=data.get("title", ""),
            company=data.get("company", ""),
            location=data.get("location"),
            job_type=data.get("job_type"),
            salary=data.get("salary"),
            posted_at=data.get("posted_at"),
            description_snippet=data.get("description_snippet"),
        )


# ---- Product items -------------------------------------------------------

@dataclass
class ProductItem(AngaliaItem):
    name: str
    price: float
    currency: str
    in_stock: bool
    rating: Optional[float] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProductItem":
        required = ["source", "external_id", "url", "scraped_at"]
        for key in required:
            if key not in data:
                raise ValueError(f"Missing required field {key}")

        hash_fields = [data["source"], data["external_id"], data["url"]]
        content_hash = _hash_content(hash_fields)

        return cls(
            source=data["source"],
            external_id=data["external_id"],
            url=data["url"],
            scraped_at=data["scraped_at"],
            content_hash=content_hash,
            name=data.get("name", ""),
            price=float(data.get("price", 0)),
            currency=data.get("currency", "KES"),
            in_stock=bool(data.get("in_stock", True)),
            rating=data.get("rating"),
        )
