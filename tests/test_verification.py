
"""Basic tests for LUVIA's verification scoring rules."""

def test_temporal_score_for_matching_timestamps():
    # Identical timestamps have zero hours of difference.
    hours_apart = 0
    score = 1 / (1 + hours_apart)

    assert score == 1.0


def test_temporal_score_for_one_hour_difference():
    # One hour of difference gives a score of 0.5.
    hours_apart = 1
    score = 1 / (1 + hours_apart)

    assert score == 0.5


def test_spatial_score_at_event_location():
    # A source at the event location has zero distance.
    distance_m = 0
    score = max(0.0, 1 - distance_m / 100_000)

    assert score == 1.0


def test_spatial_score_beyond_100_km():
    # The current spatial scoring rule bottoms out at zero.
    distance_m = 150_000
    score = max(0.0, 1 - distance_m / 100_000)

    assert score == 0.0


from contextlib import contextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.app.api.verification as verification_api


class FakeResult:
    """Simulate a database query result."""

    def mappings(self):
        return self

    def first(self):
        return None


class FakeConnection:
    """Simulate a database connection for a missing event."""

    def execute(self, query, parameters=None):
        return FakeResult()


class FakeEngine:
    """Provide a mock transaction without connecting to Neon."""

    @contextmanager
    def begin(self):
        yield FakeConnection()


def test_verification_returns_404_for_missing_event(monkeypatch):
    # Replace the real database engine with our mock.
    monkeypatch.setattr(
        verification_api, "engine", FakeEngine()
    )

    # Build a small test app containing only the verification route.
    app = FastAPI()
    app.include_router(verification_api.router)
    client = TestClient(app)

    response = client.post("/verify?event_id=999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Event not found"


from datetime import datetime, timezone


class SuccessfulFakeResult:
    """Return a simulated database row."""

    def __init__(self, row=None):
        self.row = row

    def mappings(self):
        return self

    def first(self):
        return self.row

    def all(self):
        return self.row or []

    def scalar_one(self):
        return 0.0


class SuccessfulFakeConnection:
    """Simulate event, source, and database-write queries."""

    def __init__(self):
        self.write_queries = []

    def execute(self, query, parameters=None):
        sql = str(query)
        params = parameters or {}

        # Simulate an existing event at Gurugram.
        if "FROM events e" in sql and "LEFT JOIN LATERAL" in sql:
            return SuccessfulFakeResult({
                "event_id": 6,
                "event_timestamp": datetime(
                    2026, 9, 3, 3, 0, tzinfo=timezone.utc
                ),
                "event_latitude": 28.461295,
                "event_longitude": 77.025866,
            })

        # Simulate one mock source with matching evidence.
        if "FROM sources" in sql:
            return SuccessfulFakeResult([{
                "source_type": "mock",
                "source_timestamp": datetime(
                    2026, 9, 3, 3, 0, tzinfo=timezone.utc
                ),
                "latitude": 28.461295,
                "longitude": 77.025866,
                "credibility_score": None,
            }])

        # Capture writes so we can assert they were attempted.
        self.write_queries.append((sql, params))
        return SuccessfulFakeResult()


class SuccessfulFakeEngine:
    def __init__(self):
        self.connection = SuccessfulFakeConnection()

    @contextmanager
    def begin(self):
        yield self.connection


def test_verification_saves_existing_event(monkeypatch):
    # Inject a fake database to avoid changing Neon.
    fake_engine = SuccessfulFakeEngine()
    monkeypatch.setattr(
        verification_api, "engine", fake_engine
    )

    app = FastAPI()
    app.include_router(verification_api.router)
    client = TestClient(app)

    response = client.post("/verify?event_id=6")

    assert response.status_code == 200

    body = response.json()
    assert body["event_id"] == 6
    assert body["status"] == "needs_review"
    assert body["confidence"] == 0.5

    
    # Check that both database writes were attempted.
    queries = fake_engine.connection.write_queries

    verification_writes = [
        (sql, params)
        for sql, params in queries
        if "INSERT INTO verification" in sql
    ]

    event_updates = [
        (sql, params)
        for sql, params in queries
        if "UPDATE events" in sql
    ]

    assert len(verification_writes) == 1
    assert len(event_updates) == 1


def test_event_without_sources_needs_review(monkeypatch):
    # Create a fake database that returns an existing event.
    fake_engine = SuccessfulFakeEngine()
    monkeypatch.setattr(
        verification_api, "engine", fake_engine
    )

    # Override the fake connection to return no sources.
    original_execute = fake_engine.connection.execute

    def execute_without_sources(query, parameters=None):
        sql = str(query)

        if "FROM sources" in sql:
            return SuccessfulFakeResult([])

        return original_execute(query, parameters)

    monkeypatch.setattr(
        fake_engine.connection,
        "execute",
        execute_without_sources,
    )

    app = FastAPI()
    app.include_router(verification_api.router)
    client = TestClient(app)

    response = client.post("/verify?event_id=6")

    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "needs_review"
    assert body["confidence"] == 0.0
    assert body["evidence"]["source_score"] == 0.0
    assert body["evidence"]["corroboration_score"] == 0.0


def calculate_corroboration_score(source_types):
    """Score distinct eligible source types, excluding mock data."""
    distinct_types = {
        source_type
        for source_type in source_types
        if source_type and source_type.lower() != "mock"
    }

    return min(len(distinct_types) / 3, 1.0)


def test_repeated_mock_sources_do_not_increase_corroboration():
    score = calculate_corroboration_score(
        ["mock", "mock", "mock"]
    )

    assert score == 0.0


def test_distinct_source_types_increase_corroboration():
    score = calculate_corroboration_score(
        ["weather_api", "official_alert", "news_report"]
    )

    assert score == 1.0


def test_repeated_source_types_count_only_once():
    score = calculate_corroboration_score(
        ["weather_api", "weather_api", "official_alert"]
    )

    assert abs(score - (2 / 3)) < 0.000001
