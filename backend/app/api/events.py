"""Create and retrieve events together with their related records."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from backend.app.database import engine
from backend.app.schemas.event import EventCreate

router = APIRouter(
    prefix="/events",
    tags=["Events"]
)


@router.post("")
def create_event(event: EventCreate):
    # Store the event and its location/source records as one atomic operation.

    insert_event = text("""
        INSERT INTO events (
            event_type,
            title,
            description,
            event_timestamp,
            city,
            state,
            severity
        )
        VALUES (
            :event_type,
            :title,
            :description,
            :event_timestamp,
            :city,
            :state,
            :severity
        )
        RETURNING event_id
    """)

    # Store both coordinates and a PostGIS point for spatial queries.
    insert_location = text("""
        INSERT INTO locations (
            event_id,
            latitude,
            longitude,
            city,
            state,
            geometry
        )
        VALUES (
            :event_id,
            :latitude,
            :longitude,
            :city,
            :state,
            ST_SetSRID(
                ST_MakePoint(
                    :longitude,
                    :latitude
                ),
                4326
            )::geography
        )
    """)

    # Preserve the originating source alongside the normalized event data.
    insert_source = text("""
        INSERT INTO sources (
            event_id,
            source_type,
            source_name,
            source_url,
            raw_content,
            source_timestamp,
            latitude,
            longitude
        )
        VALUES (
            :event_id,
            :source_type,
            :source_name,
            :source_url,
            :raw_content,
            :source_timestamp,
            :latitude,
            :longitude
        )
    """)

    # Commit all three inserts together or roll them back together on failure.
    with engine.begin() as connection:

        result = connection.execute(
            insert_event,
            {
                "event_type": event.event_type,
                "title": event.title,
                "description": event.description,
                "event_timestamp": event.event_timestamp,
                "city": event.city,
                "state": event.state,
                "severity": event.severity
            }
        )

        event_id = result.scalar_one()

        connection.execute(
            insert_location,
            {
                "event_id": event_id,
                "latitude": event.latitude,
                "longitude": event.longitude,
                "city": event.city,
                "state": event.state
            }
        )

        connection.execute(
            insert_source,
            {
                "event_id": event_id,
                "source_type": event.source,
                "source_name": event.source_name,
                "source_url": event.source_url,
                "raw_content": event.description,
                "source_timestamp": event.event_timestamp,
                "latitude": event.latitude,
                "longitude": event.longitude
            }
        )

    return {
        "event_id": event_id,
        "status": "created"
    }


@router.get("")
def get_events():
    # Include optional location data without hiding events that lack coordinates.

    query = text("""
        SELECT
            e.event_id,
            e.event_type,
            e.title,
            e.description,
            e.event_timestamp,
            e.city,
            e.state,
            e.severity,
            e.credibility_score,
            e.verification_status,
            l.latitude,
            l.longitude

        FROM events e

        LEFT JOIN locations l
            ON e.event_id = l.event_id

        ORDER BY e.event_timestamp DESC
    """)

    with engine.connect() as connection:
        result = connection.execute(query)

        events = [
            dict(row)
            for row in result.mappings()
        ]

    return {
        "events": events
    }


@router.get("/{event_id}")
def get_event(event_id: int):
    # Assemble the event's evidence and model results into one response.

    event_query = text("""
        SELECT
            e.*,
            l.latitude,
            l.longitude
        FROM events e

        LEFT JOIN locations l
            ON e.event_id = l.event_id

        WHERE e.event_id = :event_id
    """)

    source_query = text("""
        SELECT *
        FROM sources
        WHERE event_id = :event_id
        ORDER BY created_at DESC
    """)

    verification_query = text("""
        SELECT *
        FROM verification
        WHERE event_id = :event_id
    """)

    prediction_query = text("""
        SELECT *
        FROM model_predictions
        WHERE event_id = :event_id
        ORDER BY created_at DESC
    """)

    with engine.connect() as connection:

        event_result = connection.execute(
            event_query,
            {"event_id": event_id}
        ).mappings().first()

        # Return a clear API error instead of producing an empty detail response.
        if not event_result:
            raise HTTPException(
                status_code=404,
                detail="Event not found"
            )

        sources = [
            dict(row)
            for row in connection.execute(
                source_query,
                {"event_id": event_id}
            ).mappings()
        ]

        verification = connection.execute(
            verification_query,
            {"event_id": event_id}
        ).mappings().first()

        predictions = [
            dict(row)
            for row in connection.execute(
                prediction_query,
                {"event_id": event_id}
            ).mappings()
        ]

    return {
        "event": dict(event_result),
        "sources": sources,
        "verification": (
            dict(verification)
            if verification
            else None
        ),
        "predictions": predictions
    }