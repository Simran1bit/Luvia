
"""Expose accurate weather and verification analytics."""

from fastapi import APIRouter
from sqlalchemy import text

from backend.app.database import engine

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("")
def get_analytics():
    with engine.connect() as connection:
        totals = connection.execute(text("""
            SELECT
                COUNT(*) AS total_events,
                COUNT(*) FILTER (
                    WHERE event_type = 'weather_observation'
                ) AS weather_observations,
                COUNT(*) FILTER (
                    WHERE event_type <> 'weather_observation'
                       OR event_type IS NULL
                ) AS other_events,
                COUNT(*) FILTER (
                    WHERE LOWER(COALESCE(severity, ''))
                          IN ('high', 'critical')
                ) AS high_priority_events,
                COUNT(*) FILTER (
                    WHERE LOWER(COALESCE(verification_status, ''))
                          = 'verified'
                ) AS verified_events,
                COUNT(*) FILTER (
                    WHERE LOWER(COALESCE(verification_status, ''))
                          IN ('needs_review', 'pending')
                ) AS needs_review_events,
                MAX(event_timestamp) AS latest_event_timestamp
            FROM events
        """)).mappings().one()

        severity = [
            dict(row) for row in connection.execute(text("""
                SELECT severity, COUNT(*) AS count
                FROM events
                GROUP BY severity
                ORDER BY count DESC
            """)).mappings()
        ]

        event_types = [
            dict(row) for row in connection.execute(text("""
                SELECT event_type, COUNT(*) AS count
                FROM events
                GROUP BY event_type
                ORDER BY count DESC
            """)).mappings()
        ]

        sources = [
            dict(row) for row in connection.execute(text("""
                SELECT
                    s.source_name,
                    COUNT(DISTINCT s.event_id) AS records
                FROM sources s
                GROUP BY s.source_name
                ORDER BY records DESC
            """)).mappings()
        ]

    return {
        # Existing fields retained for compatibility
        "total_events": totals["total_events"],
        "verified_events": totals["verified_events"],
        "events_by_severity": severity,
        "events_by_type": event_types,

        # New, more transparent metrics
        "weather_observations": totals["weather_observations"],
        "other_events": totals["other_events"],
        "high_priority_events": totals["high_priority_events"],
        "needs_review_events": totals["needs_review_events"],
        "latest_event_timestamp": totals["latest_event_timestamp"],
        "records_by_source": sources,
    }