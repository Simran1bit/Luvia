"""Persist normalised LUVIA events and their supporting source records.

Kept separate from ingestion so every source (CSV, Open-Meteo, METAR, IMD
stations) stores events the same way.
"""

import json

from sqlalchemy import text

from backend.app.database import engine


def _description(data: dict) -> str:
    """Human-readable summary of the measured values (missing values are skipped)."""
    parts = []
    if data.get("temperature") is not None:
        parts.append(f"Temperature: {data['temperature']}°C")
    if data.get("humidity") is not None:
        parts.append(f"Humidity: {data['humidity']}%")
    if data.get("rainfall") is not None:
        parts.append(f"Rainfall: {data['rainfall']} mm")
    return ", ".join(parts) or "No measured values supplied."


def _raw_content(event: dict) -> str | None:
    """Serialise the readings and raw payload so the evidence can be re-analysed later."""
    if not event.get("readings") and not event.get("raw"):
        return None
    return json.dumps(
        {"readings": event.get("readings") or {}, "raw": event.get("raw")},
        default=str,
    )


def find_existing(connection, source_name, timestamp, latitude, longitude):
    """Return the event_id already holding this exact source observation, if any."""
    return connection.execute(
        text("""
            SELECT e.event_id
            FROM events e
            JOIN sources s ON s.event_id = e.event_id
            WHERE s.source_name = :source_name
              AND s.source_timestamp = CAST(:timestamp AS TIMESTAMPTZ)
              AND s.latitude = :latitude
              AND s.longitude = :longitude
            LIMIT 1
        """),
        {
            "source_name": source_name,
            "timestamp": timestamp,
            "latitude": latitude,
            "longitude": longitude,
        },
    ).scalar_one_or_none()


def find_event_near(connection, city, timestamp, source_name="OPEN_METEO", window_minutes=60):
    """Return the event for ``city`` from ``source_name`` closest in time to ``timestamp``."""
    return connection.execute(
        text("""
            SELECT e.event_id
            FROM events e
            JOIN sources s ON s.event_id = e.event_id
            WHERE s.source_name = :source_name
              AND LOWER(e.city) = LOWER(:city)
              AND s.source_timestamp BETWEEN
                  CAST(:timestamp AS TIMESTAMPTZ) - make_interval(mins => :window)
                  AND CAST(:timestamp AS TIMESTAMPTZ) + make_interval(mins => :window)
            ORDER BY ABS(EXTRACT(EPOCH FROM (s.source_timestamp - CAST(:timestamp AS TIMESTAMPTZ))))
            LIMIT 1
        """),
        {"source_name": source_name, "city": city, "timestamp": timestamp, "window": window_minutes},
    ).scalar_one_or_none()


def attach_source(connection, event_id: int, event: dict) -> None:
    """Add a further source record (e.g. a METAR) to an existing event."""
    location = event["location"]
    connection.execute(
        text("""
            INSERT INTO sources (
                event_id, source_type, source_name, raw_content,
                source_timestamp, latitude, longitude
            )
            VALUES (
                :event_id, :source_type, :source_name, :raw_content,
                :source_timestamp, :latitude, :longitude
            )
        """),
        {
            "event_id": event_id,
            "source_type": event["source"].lower(),
            "source_name": event["source"],
            "raw_content": _raw_content(event),
            "source_timestamp": event["timestamp"],
            "latitude": location["latitude"],
            "longitude": location["longitude"],
        },
    )


def update_assessment(connection, event_id, severity, status, confidence, reasons) -> None:
    """Overwrite an event's automated severity/status assessment."""
    connection.execute(
        text("""
            UPDATE events
            SET severity = :severity,
                verification_status = :status,
                credibility_score = :confidence,
                risk_reasons = CAST(:reasons AS JSONB)
            WHERE event_id = :event_id
        """),
        {
            "event_id": event_id,
            "severity": severity,
            "status": status,
            "confidence": confidence,
            "reasons": json.dumps(reasons or []),
        },
    )


def save_event(event: dict, connection=None) -> int:
    """Persist one validated LUVIA event and return its database ID.

    Uses the event's own ``severity`` / ``verification_status`` /
    ``credibility_score`` / ``risk_reasons`` when present instead of discarding
    them. Pass ``connection`` to join an outer transaction.
    """
    if connection is None:
        with engine.begin() as own_connection:
            return save_event(event, own_connection)

    location = event["location"]
    data = event.get("data") or {}

    columns = {
        "event_type": event["event_type"],
        "title": event.get("title") or f"Weather observation — {location['name']}",
        "description": event.get("description") or _description(data),
        "event_timestamp": event["timestamp"],
        "severity": event.get("severity") or "unknown",
        "verification_status": event.get("verification_status") or "unverified",
        "credibility_score": event.get("credibility_score"),
        "city": location["name"],
        "state": location.get("state"),
    }
    # risk_reasons needs database/03_live_ingestion.sql; only write it when supplied.
    if "risk_reasons" in event:
        columns["risk_reasons"] = json.dumps(event["risk_reasons"] or [])

    placeholders = ", ".join(
        "CAST(:risk_reasons AS JSONB)" if name == "risk_reasons" else f":{name}"
        for name in columns
    )
    event_id = connection.execute(
        text(f"INSERT INTO events ({', '.join(columns)}) VALUES ({placeholders}) RETURNING event_id"),
        columns,
    ).scalar_one()

    attach_source(connection, event_id, event)

    connection.execute(
        text("""
            INSERT INTO locations (event_id, latitude, longitude, city, state, geometry)
            VALUES (
                :event_id, :latitude, :longitude, :city, :state,
                ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography
            )
        """),
        {
            "event_id": event_id,
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "city": location["name"],
            "state": location.get("state"),
        },
    )

    return event_id
