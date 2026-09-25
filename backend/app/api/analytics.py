"""Expose aggregate event counts for analytics consumers."""

from fastapi import APIRouter
from sqlalchemy import text

from backend.app.database import engine

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"]
)


@router.get("")
def get_analytics():
    # Build separate aggregates so the dashboard can compare totals and trends.

    total_query = text("""
        SELECT COUNT(*) AS total
        FROM events
    """)

    # Count only events that passed the verification thresholds.
    verified_query = text("""
        SELECT COUNT(*) AS verified
        FROM events
        WHERE verification_status = 'verified'
    """)

    # Group by severity to support a distribution breakdown in the UI.
    severity_query = text("""
        SELECT
            severity,
            COUNT(*) AS count
        FROM events
        GROUP BY severity
        ORDER BY count DESC
    """)

    # Group by event type to show which kinds of events are most common.
    type_query = text("""
        SELECT
            event_type,
            COUNT(*) AS count
        FROM events
        GROUP BY event_type
        ORDER BY count DESC
    """)

    # A read-only connection is sufficient because this endpoint does not mutate data.
    with engine.connect() as connection:

        total = connection.execute(
            total_query
        ).scalar_one()

        verified = connection.execute(
            verified_query
        ).scalar_one()

        severity = [
            dict(row)
            for row in connection.execute(
                severity_query
            ).mappings()
        ]

        event_types = [
            dict(row)
            for row in connection.execute(
                type_query
            ).mappings()
        ]

    return {
        "total_events": total,
        "verified_events": verified,
        "events_by_severity": severity,
        "events_by_type": event_types
    }