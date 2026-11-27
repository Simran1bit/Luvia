"""Expose event locations and verification data for the map view."""

from fastapi import APIRouter, Query
from sqlalchemy import text

from backend.app.api.events import event_filters
from backend.app.database import engine

router = APIRouter(
    prefix="/map",
    tags=["Map"]
)


@router.get("")
def get_map_events(
    since_hours: float = Query(default=48, ge=0, description="Only events from the last N hours; 0 = all"),
    source: str = Query(default="all", description="all, live, or a source name such as METAR"),
    limit: int = Query(default=2000, ge=1, le=10000),
):
    # Return only location-bearing events so the map can place every result.
    where, params = event_filters(since_hours, source)

    query = text(f"""
        SELECT
            e.event_id,
            e.event_type,
            e.title,
            e.severity,
            e.credibility_score,
            e.verification_status,
            e.risk_reasons,
            l.latitude,
            l.longitude,
            COALESCE(e.city, l.city) AS city,
            COALESCE(e.state, l.state) AS state

        FROM events e

        JOIN locations l
            ON e.event_id = l.event_id

        {where}

        ORDER BY e.event_timestamp DESC
        LIMIT :limit
    """)

    # Close the read-only connection automatically after the result is materialized.
    with engine.connect() as connection:

        events = [
            dict(row)
            for row in connection.execute(
                query, {**params, "limit": limit}
            ).mappings() #let us work with row objects like dictionaries
        ]

    return {
        "events": events
    }