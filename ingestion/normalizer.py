# Convert raw source rows into the common LUVIA event format used by the app.
from datetime import datetime


def _to_float(value):
    """Convert a CSV value to float; empty values become None."""
    if value is None:
        return None

    value = value.strip()

    if value == "":
        return None

    return float(value)


def normalize_weather_event(row: dict) -> dict:
    """Convert one raw CSV row into the standard LUVIA event format."""

    event = {
        "event_type": "weather_observation",

        # Normalize timestamp into a standard ISO-8601 string.
        "timestamp": datetime.fromisoformat(
            row["timestamp"]
        ).isoformat(),

        "location": {
            "name": row["location_name"],
            "latitude": _to_float(row["latitude"]),
            "longitude": _to_float(row["longitude"]),
        },

        "data": {
            "temperature": _to_float(row["temperature"]),
            "humidity": _to_float(row["humidity"]),
            "rainfall": _to_float(row["rainfall"]),
        },

        # Preserve where this observation came from.
        "source": row.get("source", "unknown"),
    }

    return event

"""
# Quick smoke test for the normalizer during local development and debugging.

if __name__ == "__main__":
    sample_row = {
        "timestamp": "2026-09-01T10:00:00",
        "location_name": "Delhi_Central",
        "latitude": "28.6139",
        "longitude": "77.2090",
        "temperature": "31.2",
        "humidity": "68",
        "rainfall": "2.4",
        "source": "MOCK",
    }

    event = normalize_weather_event(sample_row)

    print(event)
"""