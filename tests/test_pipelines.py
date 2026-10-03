import datetime

import pytest
from scrapy.exceptions import DropItem
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import angalia.storage.db as db_mod
from angalia.items import JobItem, ProductItem
from angalia.pipelines import (
    DeduplicationPipeline,
    DiffPipeline,
    SQLiteStorePipeline,
    ValidationPipeline,
)
from angalia.storage.models import Base, Item, ItemHistory


class DummySpider:
    def __init__(self, name="dummy"):
        self.name = name
        self.crawler = DummyCrawler()


class DummyCrawler:
    def __init__(self):
        self.stats = DummyStats()


class DummyStats:
    def __init__(self):
        self._data = {}

    def inc_value(self, key, count=1, start=0):
        self._data[key] = self._data.get(key, start) + count

    def get_value(self, key, default=None):
        return self._data.get(key, default)

    def set_value(self, key, value):
        self._data[key] = value


@pytest.fixture
def isolated_db(monkeypatch):
    """Provide isolated in-memory SQLite engine with StaticPool for pipeline tests."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    from contextlib import contextmanager

    @contextmanager
    def mock_get_session(custom_session=None):
        sess = Session()
        try:
            yield sess
            sess.commit()
        except Exception:
            sess.rollback()
            raise
        finally:
            sess.close()

    monkeypatch.setattr(db_mod, "get_session", mock_get_session)
    monkeypatch.setattr(db_mod, "engine", engine)
    return engine, Session


@pytest.fixture
def sample_job():
    return JobItem(
        source="brightermonday",
        external_id="job-001",
        url="https://example.com/job/001",
        scraped_at=datetime.datetime(2026, 1, 1, 12, 0, 0),
        title="DevOps Engineer",
        company="Acme Corp",
        location="Nairobi",
        job_type="Full Time",
        salary="KES 200,000",
        posted_at=datetime.datetime(2026, 1, 1, 12, 0, 0),
        description_snippet="Exciting role in cloud DevOps.",
    )


@pytest.fixture
def sample_product():
    return ProductItem(
        source="jumia",
        external_id="prod-001",
        url="https://jumia.co.ke/p/001",
        scraped_at=datetime.datetime(2026, 1, 1, 12, 0, 0),
        name="Samsung TV 55",
        price=55000.0,
        currency="KES",
        in_stock=True,
        rating=4.5,
    )


def test_validation_pipeline_success(sample_job, sample_product):
    p = ValidationPipeline()
    spider = DummySpider()
    assert p.process_item(sample_job, spider) == sample_job
    assert p.process_item(sample_product, spider) == sample_product


def test_validation_pipeline_missing_base_fields(sample_job):
    p = ValidationPipeline()
    spider = DummySpider()
    sample_job.url = ""
    with pytest.raises(DropItem) as exc:
        p.process_item(sample_job, spider)
    assert "url" in str(exc.value)


def test_validation_pipeline_missing_job_fields(sample_job):
    p = ValidationPipeline()
    spider = DummySpider()
    sample_job.title = ""
    with pytest.raises(DropItem) as exc:
        p.process_item(sample_job, spider)
    assert "title" in str(exc.value)


def test_validation_pipeline_missing_product_fields(sample_product):
    p = ValidationPipeline()
    spider = DummySpider()
    sample_product.name = ""
    with pytest.raises(DropItem) as exc:
        p.process_item(sample_product, spider)
    assert "name" in str(exc.value)


def test_deduplication_pipeline(sample_job, isolated_db):
    _, Session = isolated_db
    now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
    with Session() as session:
        session.add(
            Item(
                source=sample_job.source,
                external_id=sample_job.external_id,
                url=sample_job.url,
                data=sample_job.to_dict(),
                content_hash=sample_job.content_hash,
                first_seen=now,
                last_seen=now,
            )
        )
        session.commit()

    dedup = DeduplicationPipeline()
    spider = DummySpider()

    # Identical item -> dropped
    with pytest.raises(DropItem) as exc:
        dedup.process_item(sample_job, spider)
    assert "Duplicate content_hash" in str(exc.value)

    # Different item -> allowed
    different_job = JobItem(
        source="brightermonday",
        external_id="job-002",
        url="https://example.com/job/002",
        title="QA Engineer",
        company="Acme Corp",
    )
    result = dedup.process_item(different_job, spider)
    assert result == different_job


def test_diff_and_sqlite_store_pipeline(sample_job, isolated_db):
    spider = DummySpider()
    diff_pipe = DiffPipeline()
    store_pipe = SQLiteStorePipeline()

    # 1. First run -> NEW event emitted and saved
    diff_pipe.process_item(sample_job, spider)
    assert hasattr(sample_job, "_change_events")
    assert len(sample_job._change_events) == 1
    assert sample_job._change_events[0].type == "NEW"

    store_pipe.process_item(sample_job, spider)

    _, Session = isolated_db
    with Session() as session:
        stored = session.query(Item).filter_by(source=sample_job.source, external_id=sample_job.external_id).one()
        assert stored.external_id == "job-001"
        assert stored.data["title"] == "DevOps Engineer"
        # No history entries for initial creation
        assert session.query(ItemHistory).count() == 0

    # 2. Second run with update -> UPDATED event recorded in history
    sample_job.salary = "KES 250,000"
    sample_job.content_hash = ""
    sample_job.__post_init__()

    diff_pipe.process_item(sample_job, spider)
    assert len(sample_job._change_events) == 1
    assert sample_job._change_events[0].type == "UPDATED"
    assert sample_job._change_events[0].field == "salary"

    store_pipe.process_item(sample_job, spider)

    with Session() as session:
        updated_item = session.query(Item).filter_by(source=sample_job.source, external_id=sample_job.external_id).one()
        assert updated_item.data["salary"] == "KES 250,000"

        history_rows = session.query(ItemHistory).filter_by(item_id=updated_item.id).all()
        assert len(history_rows) == 1
        assert history_rows[0].field == "salary"
        assert history_rows[0].old_value == "KES 200,000"
        assert history_rows[0].new_value == "KES 250,000"
