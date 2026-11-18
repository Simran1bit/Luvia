
from collections import Counter, defaultdict
from datetime import date, datetime

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from backend.app.database import engine
from backend.app.ingestion.adapters.imd_warning_adapter import (
    fetch_imd_district_warnings,
)
from backend.app.services.imd_warning_persistence import save_imd_warnings

router = APIRouter(
    prefix="/imd-warnings",
    tags=["IMD Official Warnings"],
)

SOURCE_URL = (
    "https://mausam.imd.gov.in/responsive/"
    "districtWiseWarningGIS.php"
)

# Based on the colour-code mapping used by the frontend.
COLOUR_NAMES = {
    "1": "green",
    "2": "yellow",
    "3": "orange",
    "4": "red",
}

WARNING_TYPES = {
    "1": "No Warning",
    "2": "Heavy Rain",
    "3": "Heavy Snow",
    "4": "Thunderstorm & Lightning",
    "5": "Hailstorm",
    "6": "Dust Storm",
    "7": "Dust Raising Winds",
    "8": "Strong Surface Winds",
    "9": "Heat Wave",
    "10": "Hot Day",
    "11": "Warm Night",
    "12": "Cold Wave",
    "13": "Cold Day",
    "14": "Ground Frost",
    "15": "Fog",
    "16": "Very Heavy Rain",
    "17": "Extremely Heavy Rain",
}


def serialize_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


@router.get("/")
def get_imd_warnings(
    district: str | None = Query(default=None),
    limit: int = Query(default=756, ge=1, le=1000),
):
    """Return stored official IMD district warnings."""
    query = """
        SELECT
            warning_id,
            district,
            state,
            issue_date,
            source_updated_at,
            fetched_at,
            days,
            source_name,
            source_url
        FROM imd_district_warnings
    """
    params = {"limit": limit}

    if district:
        query += " WHERE LOWER(district) = LOWER(:district)"
        params["district"] = district.strip()

    query += " ORDER BY district LIMIT :limit"

    try:
        with engine.connect() as connection:
            rows = connection.execute(
                text(query), params
            ).mappings().all()

        warnings = []
        for row in rows:
            item = dict(row)

            for key in ("issue_date", "source_updated_at", "fetched_at"):
                item[key] = serialize_value(item.get(key))

            item["days"] = item["days"] or []
            warnings.append(item)

        return {
            "source": "India Meteorological Department (IMD)",
            "source_url": SOURCE_URL,
            "count": len(warnings),
            "warnings": warnings,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not read stored IMD warnings: {exc}",
        ) from exc


@router.post("/refresh")
def refresh_imd_warnings():
    """Fetch and store the latest IMD district warnings."""
    try:
        records = fetch_imd_district_warnings()
        result = save_imd_warnings(records)

        return {
            "message": "IMD warning refresh completed",
            "received": len(records),
            **result,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not refresh IMD warnings: {exc}",
        ) from exc


@router.get("/analytics")
def get_imd_warning_analytics():
    """
    Summarize warning codes, colours and unique districts by forecast day.

    Day 1 means the first forecast day supplied by IMD; it is not
    automatically assumed to mean the current calendar day.
    """
    try:
        with engine.connect() as connection:
            rows = connection.execute(
                text("""
                    SELECT
                        district,
                        state,
                        issue_date,
                        fetched_at,
                        days
                    FROM imd_district_warnings
                """)
            ).mappings().all()

        warning_codes = Counter()
        color_codes = Counter()
        day_counts = Counter()
        districts_by_state = defaultdict(set)

        # Each set counts a district only once for a given forecast day/colour.
        districts_by_day_colour = defaultdict(set)
        warning_types_by_day = defaultdict(Counter)
        districts_by_day = defaultdict(set)

        latest_fetched_at = None
        issue_dates = set()

        for row in rows:
            district = (row["district"] or "").strip()
            state = row["state"] or "Unknown state"

            if district:
                districts_by_state[state].add(district)

            issue_date = row["issue_date"]
            if issue_date is not None:
                issue_dates.add(str(issue_date))

            fetched_at = row["fetched_at"]
            if fetched_at is not None and (
                latest_fetched_at is None
                or fetched_at > latest_fetched_at
            ):
                latest_fetched_at = fetched_at

            for item in row["days"] or []:
                day = str(item.get("day", "")).strip()
                code = item.get("warning_code")
                color = item.get("color_code")

                if day:
                    day_counts[day] += 1
                    if district:
                        districts_by_day[day].add(district)

                if code is not None and str(code).strip():
                    codes = [
                        value.strip()
                        for value in str(code).split(",")
                        if value.strip()
                    ]

                    for individual_code in codes:
                        warning_codes[individual_code] += 1

                        warning_name = WARNING_TYPES.get(
                            individual_code,
                            f"Unknown warning ({individual_code})",
                        )

                        if day and district:
                            warning_types_by_day[day][warning_name] += 1

                if color is not None and str(color).strip():
                    color_key = str(color).strip()
                    color_codes[color_key] += 1

                    if day and district:
                        districts_by_day_colour[
                            (day, color_key)
                        ].add(district)

        # Unique district totals, split by forecast day and colour.
        day_colour_summary = {}

        for day in sorted(day_counts, key=lambda value: int(value)):
            day_colour_summary[day] = {
                colour_name: len(
                    districts_by_day_colour.get((day, colour_code), set())
                )
                for colour_code, colour_name in COLOUR_NAMES.items()
            }

        # Unique districts with orange/red warnings on each forecast day.
        severe_districts_by_day = {}

        for day in sorted(day_counts, key=lambda value: int(value)):
            severe = set()
            for colour_code in ("3", "4"):
                severe.update(
                    districts_by_day_colour.get((day, colour_code), set())
                )

            severe_districts_by_day[day] = len(severe)

        # Preserve legacy fields so existing frontend charts still work.
        return {
            "source": "India Meteorological Department (IMD)",
            "source_url": SOURCE_URL,
            "stored_district_records": len(rows),
            "latest_fetched_at": serialize_value(latest_fetched_at),
            "issue_dates": sorted(issue_dates),
            "distinct_warning_codes": dict(warning_codes),
            "color_code_counts": dict(color_codes),
            "records_by_forecast_day": dict(day_counts),
            "records_by_state": {
                state: len(districts)
                for state, districts in districts_by_state.items()
            },

            # New fields for the dashboard and verification workflow.
            "districts_by_forecast_day": {
                day: len(districts)
                for day, districts in districts_by_day.items()
            },
            "districts_by_day_colour": day_colour_summary,
            "orange_red_districts_by_day": severe_districts_by_day,
            "warning_types_by_day": {
                day: dict(counts)
                for day, counts in warning_types_by_day.items()
            },
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not calculate IMD analytics: {exc}",
        ) from exc
