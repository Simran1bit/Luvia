from fastapi.testclient import TestClient
from sqlalchemy import text

from backend.app.main import app, engine


def test_database_health():
    response = TestClient(app).get("/health/db")

    assert response.status_code == 200
    assert response.json() == {"database": "connected", "result": 1}


def test_stored_events_can_be_read():
    response = TestClient(app).get("/events")

    assert response.status_code == 200
    events = response.json()["events"]
    assert events, "Expected at least one stored event in Neon"
    assert {"event_id", "event_type", "title"} <= events[0].keys()


def test_events_table_row_count():
    with engine.connect() as connection:
        row_count = connection.execute(
            text("SELECT COUNT(*) FROM events")
        ).scalar_one()

    assert isinstance(row_count, int)
    assert row_count > 0, "Expected at least one row in the events table"
