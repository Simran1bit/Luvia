
"""Import historical Open-Meteo observations into LUVIA."""

import json
from pathlib import Path

from sqlalchemy import text

from backend.app.database import engine
from backend.app.ingestion.normalizer import normalize_weather_event
from backend.app.ingestion.validator import validate_weather_event
from backend.app.services.event_persistence import save_event


PREVIEW_FILE = Path("data/processed/historical_weather_preview.json")


def main():
    if not PREVIEW_FILE.exists():
        raise FileNotFoundError(
            f"Preview not found: {PREVIEW_FILE}. Run historical ingestion first."
        )

    with PREVIEW_FILE.open("r", encoding="utf-8") as file:
        rows = json.load(file)

    saved = 0
    skipped = 0
    failed = 0

    for row in rows:
        try:
            event = normalize_weather_event(row)
            event["source"] = "OPEN_METEO_ARCHIVE"

            valid, errors = validate_weather_event(event)
            if not valid:
                print(f"Skipped invalid {row['location_name']}: {errors}")
                failed += 1
                continue

            location = event["location"]

            with engine.connect() as connection:
                existing = connection.execute(
                    text("""
                        SELECT 1
                        FROM events e
                        JOIN sources s ON s.event_id = e.event_id
                        WHERE s.source_name = :source_name
                          AND s.source_timestamp =
                              CAST(:timestamp AS TIMESTAMPTZ)
                          AND s.latitude = :latitude
                          AND s.longitude = :longitude
                        LIMIT 1
                    """),
                    {
                        "source_name": event["source"],
                        "timestamp": event["timestamp"],
                        "latitude": location["latitude"],
                        "longitude": location["longitude"],
                    },
                ).scalar_one_or_none()

            if existing:
                skipped += 1
                continue

            save_event(event)
            saved += 1

            if saved % 250 == 0:
                print(f"Imported {saved} new observations...")

        except Exception as exc:
            failed += 1
            print(
                f"Failed {row.get('location_name', 'unknown city')} "
                f"at {row.get('timestamp', 'unknown time')}: {exc}"
            )

    with engine.connect() as connection:
        total = connection.execute(
            text("SELECT COUNT(*) FROM events")
        ).scalar_one()

        historical_total = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM events e
                JOIN sources s ON s.event_id = e.event_id
                WHERE s.source_name = 'OPEN_METEO_ARCHIVE'
            """)
        ).scalar_one()

    print("\n--- Historical Import Summary ---")
    print(f"Preview rows: {len(rows)}")
    print(f"New observations imported: {saved}")
    print(f"Existing observations skipped: {skipped}")
    print(f"Failures: {failed}")
    print(f"Historical observations in database: {historical_total}")
    print(f"Total event records in database: {total}")


if __name__ == "__main__":
    main()
