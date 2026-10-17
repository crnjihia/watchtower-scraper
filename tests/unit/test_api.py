from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from watchtower.api.main import app
from watchtower.db.models import Base, ChangeEvent, ChangeKind, Item, SpiderRun
from watchtower.db.session import get_db_session


@pytest.fixture
def api_client(tmp_path: Any) -> TestClient:
    engine = create_engine(f"sqlite:///{tmp_path}/test_api.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    def override_get_db() -> Any:
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db_session] = override_get_db

    # Pre-populate sample items, runs, and events
    session = session_factory()
    run = SpiderRun(spider="jumia", items_seen=10, errors=0, status="completed")
    item = Item(site="jumia", external_id="api-101", url="https://jumia.co.ke/101", title="API Phone")
    session.add_all([run, item])
    session.commit()

    ev = ChangeEvent(item_id=item.id, kind=ChangeKind.NEW_LISTING, diff={"test": 1})
    session.add(ev)
    session.commit()
    session.close()

    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
    engine.dispose()


def test_health_endpoint(api_client: TestClient) -> None:
    resp = api_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["database"] == "healthy"


def test_runs_endpoint(api_client: TestClient) -> None:
    resp = api_client.get("/runs?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["spider"] == "jumia"
    assert data[0]["status"] == "completed"


def test_changes_endpoint(api_client: TestClient) -> None:
    resp = api_client.get("/changes?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["title"] == "API Phone"
    assert data[0]["kind"] == "new_listing"

    unnotified_resp = api_client.get("/changes?unnotified_only=true")
    assert unnotified_resp.status_code == 200
    assert len(unnotified_resp.json()) >= 1
