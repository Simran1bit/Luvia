
"""Fetch, validate, and persist current weather across India."""

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import text

from backend.app.database import engine
from backend.app.ingestion.adapters.open_meteo_adapter import fetch_india_weather
from backend.app.ingestion.normalizer import normalize_weather_event
from backend.app.ingestion.validator import validate_weather_event
from backend.app.services.event_persistence import save_event


def main():
    snapshots, failures = fetch_india_weather()

    saved = 0
    skipped = 0
    failed = len(failures)

    for row in snapshots:
        try:
            local_time = datetime.fromisoformat(row["timestamp"])
            if local_time.tzinfo is None:
                row["timestamp"] = local_time.replace(
                    tzinfo=ZoneInfo("Asia/Kolkata")
                ).isoformat()

            event = normalize_weather_event(row)
            is_valid, errors = validate_weather_event(event)

            if not is_valid:
                print(f"Invalid record for {row['location_name']}: {errors}")
                failed += 1
                continue

            location = event["location"]
            timestamp = event["timestamp"]

            duplicate_query = text("""
                SELECT e.event_id
                FROM events e
                JOIN sources s ON s.event_id = e.event_id
                WHERE s.source_name = :source_name
                  AND s.source_timestamp = CAST(:timestamp AS TIMESTAMPTZ)
                  AND s.latitude = :latitude
                  AND s.longitude = :longitude
                LIMIT 1
            """)

            with engine.connect() as connection:
                existing = connection.execute(
                    duplicate_query,
                    {
                        "source_name": event["source"],
                        "timestamp": timestamp,
                        "latitude": location["latitude"],
                        "longitude": location["longitude"],
                    },
                ).scalar_one_or_none()

            
            if existing is not None:
                # Backfill city/state for snapshots saved before state support.
                with engine.begin() as connection:
                    connection.execute(
                        text("""
                            UPDATE events
                            SET city = :city, state = :state
                            WHERE event_id = :event_id
                        """),
                        {
                            "event_id": existing,
                            "city": location["name"],
                            "state": location.get("state"),
                        },
                    )

                    connection.execute(
                        text("""
                            UPDATE locations
                            SET city = :city, state = :state
                            WHERE event_id = :event_id
                        """),
                        {
                            "event_id": existing,
                            "city": location["name"],
                            "state": location.get("state"),
                        },
                    )

                print(
                    f"Updated existing record: {location['name']}, "
                    f"{location.get('state')}"
                )
                skipped += 1
                continue

            event_id = save_event(event)
            print(
                f"Saved event {event_id}: "
                f"{location['name']}, {location.get('state') or 'State unavailable'}"
            )
            saved += 1

        except Exception as exc:
            print(f"Failed to process {row.get('location_name', 'location')}: {exc}")
            failed += 1

    print("\n--- LUVIA India Weather Ingestion Summary ---")
    print(f"Snapshots received: {len(snapshots)}")
    print(f"New events saved: {saved}")
    print(f"Duplicates skipped: {skipped}")
    print(f"Failures: {failed}")


if __name__ == "__main__":
    main()
