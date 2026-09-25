from fastapi import APIRouter
from sqlalchemy import text

from backend.app.database import engine

router = APIRouter(
    prefix="/map",
    tags=["Map"]
)


@router.get("")
def get_map_events():

    query = text("""
        SELECT
            e.event_id,
            e.event_type,
            e.title,
            e.severity,
            e.credibility_score,
            e.verification_status,
            l.latitude,
            l.longitude,
            l.city,
            l.state

        FROM events e

        JOIN locations l
            ON e.event_id = l.event_id

        ORDER BY e.event_timestamp DESC
    """)

    with engine.connect() as connection:

        events = [
            dict(row)
            for row in connection.execute(
                query
            ).mappings()
        ]

    return {
        "events": events
    }