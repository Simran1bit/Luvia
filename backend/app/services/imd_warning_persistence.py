
import json
from datetime import date, datetime

from sqlalchemy import text

from backend.app.database import engine


def _parse_issue_date(value):
    """Parse an IMD issue date without inventing a date when it is missing."""
    if not value:
        return None

    value = str(value).strip()

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d-%b-%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _parse_timestamp(value):
    """Convert a timestamp to a Python datetime, if possible."""
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(
            str(value).strip().replace("Z", "+00:00")
        )
        return parsed
    except ValueError:
        return None


def save_imd_warnings(records):
    """Insert or refresh IMD district warning snapshots."""
    query = text("""
        INSERT INTO imd_district_warnings (
            district,
            state,
            issue_date,
            source_updated_at,
            fetched_at,
            days,
            source_name,
            source_url
        )
        VALUES (
            :district,
            :state,
            :issue_date,
            :source_updated_at,
            CURRENT_TIMESTAMP,
            CAST(:days AS JSONB),
            'IMD',
            :source_url
        )
        ON CONFLICT (district, issue_date, source_name)
        DO UPDATE SET
            state = COALESCE(EXCLUDED.state, imd_district_warnings.state),
            source_updated_at = EXCLUDED.source_updated_at,
            fetched_at = CURRENT_TIMESTAMP,
            days = EXCLUDED.days,
            source_url = EXCLUDED.source_url
    """)

    saved = 0
    skipped = 0

    with engine.begin() as connection:
        for record in records:
            district = (record.get("district") or "").strip()
            if not district:
                skipped += 1
                continue

            params = {
                "district": district,
                "state": record.get("state"),
                "issue_date": _parse_issue_date(record.get("issue_date")),
                "source_updated_at": _parse_timestamp(
                    record.get("updated_at")
                ),
                "days": json.dumps(record.get("days") or []),
                "source_url": (
                    "https://mausam.imd.gov.in/responsive/"
                    "districtWiseWarningGIS.php"
                ),
            }

            # NULL issue dates cannot reliably deduplicate with a normal
            # UNIQUE constraint, so don't insert them until their date
            # can be parsed.
            if params["issue_date"] is None:
                skipped += 1
                continue

            connection.execute(query, params)
            saved += 1

    return {"saved": saved, "skipped": skipped}
