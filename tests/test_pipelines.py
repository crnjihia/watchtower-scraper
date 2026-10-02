import datetime
import json
import pytest
from angalia.pipelines import ValidationPipeline, DeduplicationPipeline, SQLiteStorePipeline, DiffPipeline
from angalia.items import JobItem
from angalia.storage.db import get_session, engine
from angalia.storage.models import Item

# Use in-memory SQLite for tests
engine.url = "sqlite:///:memory:"

@pytest.fixture
def sample_job():
    return JobItem(
        source="brightermonday",
        external_id="job-001",
        url="https://example.com/job/001",
        scraped_at=datetime.datetime.utcnow(),
        title="DevOps Engineer",
        company="Acme Corp",
        location="Nairobi",
        job_type="Full‑time",
        salary="KES 200k",
        posted_at=datetime.datetime.utcnow(),
        description_snippet="Exciting role...",
    )

def test_validation_pipeline(sample_job):
    p = ValidationPipeline()
    assert p.process_item(sample_job, spider=type("S", (), {"name": "test"})) == sample_job

def test_deduplication_pipeline(sample_job, monkeypatch):
    # Insert duplicate
    with get_session() as session:
        session.add(
            Item(
                source=sample_job.source,
                external_id=sample_job.external_id,
                url=sample_job.url,
                data=json.dumps(sample_job.__dict__),
                content_hash=sample_job.content_hash,
                first_seen=datetime.datetime.utcnow(),
                last_seen=datetime.datetime.utcnow(),
            )
        )
        session.commit()
    p = DeduplicationPipeline()
    with pytest.raises(Exception) as exc:
        p.process_item(sample_job, spider=type("S", (), {"name": "test"}))
    assert "Duplicate content_hash" in str(exc.value)

def test_sqlite_store_pipeline(sample_job):
    p = SQLiteStorePipeline()
    item = p.process_item(sample_job, spider=type("S", (), {"name": "test"}))
    with get_session() as session:
        stored = session.query(Item).filter_by(source=sample_job.source, external_id=sample_job.external_id).one()
        assert stored is not None
        loaded = json.loads(stored.data)
        assert loaded["title"] == "DevOps Engineer"

def test_diff_pipeline(sample_job):
    diff_pipe = DiffPipeline()
    dummy_spider = type("Spider", (), {"crawler": type("C", (), {"stats": type("S", (), {"inc_value": lambda *a, **k: None, "get_value": lambda *a, **k: [], "set_value": lambda *a, **k: None})()})()})
    diff_pipe.process_item(sample_job, dummy_spider)
    # Simulate an update
    sample_job.salary = "KES 210k"
    diff_pipe.process_item(sample_job, dummy_spider)
    events = dummy_spider.crawler.stats.get_value("change_events_list")
    assert len(events) >= 2
    assert any(ev["type"] == "NEW" for ev in events)
    assert any(ev["type"] == "UPDATED" and ev["field"] == "salary" for ev in events)
