"""Official IMD current-weather station observations (disabled until whitelisted).

IMD serves station observations at
    https://api.imd.gov.in/api/v1/current_wx?id=<station id>
but only to IP addresses it has whitelisted. Request access at
    https://city.imd.gov.in/citywx/api_request.php
then email IMD to confirm, as the form instructs.

Until approval this adapter is off. Enable it with:
    IMD_API_ENABLED=true
    IMD_API_BASE=https://api.imd.gov.in/api/v1   (optional override)
and fill in ``imd_station_id`` for cities in ``backend/app/ingestion/locations.py``.

The response schema could not be inspected without whitelisting, so readings
are extracted with the tolerant alias-based extractor in ``severity.py``.
Check one real response once access works, and tighten the parser if needed.
"""

import json
import logging
import os
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from backend.app.ai.severity import extract_readings
from backend.app.ingestion.locations import INDIAN_LOCATIONS

logger = logging.getLogger(__name__)
USER_AGENT = "LUVIA-Weather-Intelligence/1.0"


def is_enabled() -> bool:
    return os.getenv("IMD_API_ENABLED", "").strip().lower() in ("1", "true", "yes")


def _first(payload: dict, *keys):
    for key in keys:
        for candidate in (key, key.lower(), key.upper()):
            if candidate in payload and payload[candidate] not in (None, ""):
                return payload[candidate]
    return None


def parse_station_payload(payload, location: dict) -> dict:
    """Best-effort conversion of an IMD station response into a raw observation row."""
    record = payload[0] if isinstance(payload, list) and payload else payload
    if not isinstance(record, dict):
        raise ValueError("Unexpected IMD station response shape.")

    readings = extract_readings(record)
    timestamp = _first(record, "Date_Time", "date_time", "datetime", "obs_time", "time")

    return {
        "timestamp": str(timestamp) if timestamp else datetime.now(timezone.utc).isoformat(),
        "location_name": location["location_name"],
        "state": location.get("state"),
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "temperature": readings.get("temp_c"),
        "humidity": _first(record, "Humidity", "rh", "relative_humidity"),
        "rainfall": readings.get("rain_1h_mm"),
        "source": "IMD_STATION",
        "station": location.get("imd_station_id"),
        "readings": readings,
        "raw": record,
    }


def fetch_imd_station_observations(locations=None):
    """Return ``(rows, failures)``; empty when the integration is disabled."""
    if not is_enabled():
        logger.info("IMD station API disabled (IMD_API_ENABLED is not set; whitelisting pending).")
        return [], []

    base = os.getenv("IMD_API_BASE", "https://api.imd.gov.in/api/v1").rstrip("/")
    locations = [loc for loc in (locations or INDIAN_LOCATIONS) if loc.get("imd_station_id")]
    rows, failures = [], []

    for location in locations:
        url = f"{base}/current_wx?{urlencode({'id': location['imd_station_id']})}"
        try:
            request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            with urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            rows.append(parse_station_payload(payload, location))
        except Exception as exc:
            failures.append({"location": location["location_name"], "error": str(exc)})

    return rows, failures
