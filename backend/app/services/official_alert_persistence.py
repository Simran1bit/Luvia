"""Store official CAP alerts (NDMA SACHET) in the ``official_alerts`` table."""

import json

from sqlalchemy import text

from backend.app.database import engine


def known_identifiers(connection, days: int = 7) -> set[str]:
    """Identifiers already stored recently, so their CAP documents are not re-downloaded."""
    rows = connection.execute(
        text("""
            SELECT identifier
            FROM official_alerts
            WHERE source = 'SACHET'
              AND fetched_at >= NOW() - make_interval(days => :days)
        """),
        {"days": days},
    ).scalars()
    return set(rows)


def save_official_alerts(alerts: list[dict]) -> dict:
    """Insert or refresh SACHET alerts; returns counts."""
    query = text("""
        INSERT INTO official_alerts (
            identifier, source, sender, event, category, severity, cap_severity,
            urgency, certainty, headline, title, description, instruction, area,
            effective_at, expires_at, published_at, link, raw, fetched_at
        )
        VALUES (
            :identifier, 'SACHET', :sender, :event, :category, :severity, :cap_severity,
            :urgency, :certainty, :headline, :title, :description, :instruction, :area,
            CAST(:effective_at AS TIMESTAMPTZ), CAST(:expires_at AS TIMESTAMPTZ),
            CAST(:published_at AS TIMESTAMPTZ), :link, CAST(:raw AS JSONB), CURRENT_TIMESTAMP
        )
        ON CONFLICT (identifier) DO UPDATE SET
            severity = EXCLUDED.severity,
            expires_at = EXCLUDED.expires_at,
            raw = EXCLUDED.raw,
            fetched_at = CURRENT_TIMESTAMP
    """)

    saved = 0
    with engine.begin() as connection:
        for alert in alerts:
            connection.execute(query, {
                "identifier": alert["identifier"],
                "sender": alert.get("sender") or alert.get("author"),
                "event": alert.get("event"),
                "category": alert.get("cap_category") or alert.get("category"),
                "severity": alert.get("severity") or "unknown",
                "cap_severity": alert.get("cap_severity"),
                "urgency": alert.get("urgency"),
                "certainty": alert.get("certainty"),
                "headline": alert.get("headline"),
                "title": alert.get("title"),
                "description": alert.get("description"),
                "instruction": alert.get("instruction"),
                "area": alert.get("area"),
                "effective_at": alert.get("effective_at"),
                "expires_at": alert.get("expires_at"),
                "published_at": alert.get("published_at"),
                "link": alert.get("link"),
                "raw": json.dumps(alert, default=str),
            })
            saved += 1

    return {"saved": saved}
