"""Expose official CAP alerts (NDMA SACHET) stored by the live ingestion."""

from fastapi import APIRouter, Query
from sqlalchemy import text

from backend.app.database import engine

router = APIRouter(prefix="/alerts", tags=["Official Alerts"])


@router.get("")
def get_alerts(
    active_only: bool = Query(default=True, description="Only alerts that have not expired"),
    severity: str | None = Query(default=None, description="critical, high, medium, low"),
    area: str | None = Query(default=None, description="Case-insensitive match on the alert area"),
    limit: int = Query(default=200, ge=1, le=1000),
):
    conditions = ["source = 'SACHET'"]
    params = {"limit": limit}

    if active_only:
        # Alerts without an expiry are kept for 24 hours after publication.
        conditions.append(
            "(expires_at > NOW() OR (expires_at IS NULL AND published_at > NOW() - INTERVAL '24 hours'))"
        )
    if severity:
        conditions.append("severity = :severity")
        params["severity"] = severity.strip().lower()
    if area:
        conditions.append("area ILIKE :area")
        params["area"] = f"%{area.strip()}%"

    query = text(f"""
        SELECT identifier, source, sender, event, category, severity, cap_severity,
               urgency, certainty, COALESCE(headline, title) AS headline, instruction,
               area, effective_at, expires_at, published_at, link
        FROM official_alerts
        WHERE {' AND '.join(conditions)}
        ORDER BY
            CASE severity WHEN 'critical' THEN 4 WHEN 'high' THEN 3
                          WHEN 'medium' THEN 2 WHEN 'low' THEN 1 ELSE 0 END DESC,
            published_at DESC NULLS LAST
        LIMIT :limit
    """)

    with engine.connect() as connection:
        alerts = [dict(row) for row in connection.execute(query, params).mappings()]

    return {
        "source": "NDMA SACHET (CAP)",
        "source_url": "https://sachet.ndma.gov.in/",
        "count": len(alerts),
        "alerts": alerts,
    }
