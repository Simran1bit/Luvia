# Taking a validated LUVIA event and persisting it to the database. 
# This is a separate service to keep the code clean and maintainable.

from sqlalchemy import text

from backend.app.database import engine


def save_event(event: dict) -> int:
    """Persist one validated LUVIA event and return its database ID."""

    location = event["location"]
    data = event["data"]

    # Build a readable database title from the event information.
    title = f"Weather observation — {location['name']}"

    # Keep the initial description human-readable for debugging and inspection.
    description = (
        f"Temperature: {data['temperature']}°C, "
        f"Humidity: {data['humidity']}%, "
        f"Rainfall: {data['rainfall']} mm"
    )

    # One transaction keeps the event, source, and location inserts together.
    with engine.begin() as connection:

        # Insert the parent event first so we can obtain its generated ID.
        result = connection.execute(
            text(
                """
                INSERT INTO events (
                    event_type,
                    title,
                    description,
                    event_timestamp,
                    severity,
                    verification_status
                )
                VALUES (
                    :event_type,
                    :title,
                    :description,
                    :event_timestamp,
                    :severity,
                    :verification_status
                )
                RETURNING event_id
                """
            ),
            {
                "event_type": event["event_type"],
                "title": title,
                "description": description,
                "event_timestamp": event["timestamp"],
                "severity": "unknown",
                "verification_status": "unverified",
            },
        )

        # PostgreSQL generated this ID for the new event.
        event_id = result.scalar_one()

        # Store where the event came from.
        connection.execute(
            text(
                """
                INSERT INTO sources (
                    event_id,
                    source_type,
                    source_name,
                    source_timestamp,
                    latitude,
                    longitude
                )
                VALUES (
                    :event_id,
                    :source_type,
                    :source_name,
                    :source_timestamp,
                    :latitude,
                    :longitude
                )
                """
            ),
            {
                "event_id": event_id,
                "source_type": event["source"].lower(),
                "source_name": event["source"],
                "source_timestamp": event["timestamp"],
                "latitude": location["latitude"],
                "longitude": location["longitude"],
            },
        )

        # Store the event's geographic location as a PostGIS point.
        connection.execute(
            text(
                """
                INSERT INTO locations (
                    event_id,
                    latitude,
                    longitude,
                    city,
                    geometry
                )
                VALUES (
                    :event_id,
                    :latitude,
                    :longitude,
                    :city,
                    ST_SetSRID(
                        ST_MakePoint(:longitude, :latitude),
                        4326
                    )::geography
                )
                """
            ),
            {
                "event_id": event_id,
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "city": location["name"],
            },
        )

    return event_id