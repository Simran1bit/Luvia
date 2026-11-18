
# Convert raw source rows into the common LUVIA event format used by the app.
from datetime import datetime


def _to_float(value):
    """Convert numeric or string values to float safely."""
    if value is None:
        return None

    if isinstance(value, str):
        value = value.strip()

        if value == "":
            return None

    return float(value)


def classify_weather_severity(rainfall):
    """
    Classify rainfall intensity using simple, configurable thresholds.

    These are preliminary application thresholds, not official IMD
    warning criteria. Missing rainfall remains unknown.
    """
    if rainfall is None:
        return "unknown"

    if rainfall < 0:
        return "unknown"

    if rainfall < 2.5:
        return "low"

    if rainfall < 15.6:
        return "medium"

    if rainfall < 64.5:
        return "high"

    return "critical"


def normalize_weather_event(row: dict) -> dict:
    """Convert one raw weather row into LUVIA's common event format."""

    temperature = _to_float(row.get("temperature"))
    humidity = _to_float(row.get("humidity"))
    rainfall = _to_float(row.get("rainfall"))

    event = {
        "event_type": "weather_observation",
        "timestamp": datetime.fromisoformat(
            row["timestamp"]
        ).isoformat(),

        "location": {
            "name": row["location_name"],
            "state": row.get("state"),
            "latitude": _to_float(row.get("latitude")),
            "longitude": _to_float(row.get("longitude")),
        },

        "data": {
            "temperature": temperature,
            "humidity": humidity,
            "rainfall": rainfall,
        },

        "severity": classify_weather_severity(rainfall),
        "source": row.get("source", "unknown"),
    }

    return event
