"""Fetch current weather for every registered Indian city from Open-Meteo.

Open-Meteo accepts comma-separated coordinates, so all cities are fetched in a
few batched requests instead of one request per city.

Each returned row is in LUVIA's raw observation format (what
``normalizer.normalize_weather_event`` expects) plus:

* ``readings`` - keys understood by ``backend.app.ai.severity.classify_readings``
* ``raw``      - the untouched Open-Meteo values, kept as evidence
"""

import json
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from backend.app.ingestion.locations import INDIAN_LOCATIONS  # noqa: F401  (re-exported)

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
USER_AGENT = "LUVIA-Weather-Intelligence/1.0"
BATCH_SIZE = 50

CURRENT_FIELDS = (
    "temperature_2m,relative_humidity_2m,precipitation,rain,weather_code,"
    "wind_speed_10m,wind_gusts_10m,pressure_msl,cloud_cover"
)


def _request_json(params: dict, timeout: int = 30):
    url = f"{FORECAST_URL}?{urlencode(params)}"
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _rain_totals(hourly: dict, current_time: str) -> tuple[float | None, float | None]:
    """Return (last hour, last 24 hours) precipitation up to the current hour.

    Open-Meteo hourly precipitation at time T is the total for the hour ending
    at T. Only hours at or before the current observation time are counted, so
    no forecast values leak into the totals.
    """
    times = hourly.get("time") or []
    values = hourly.get("precipitation") or []
    if not times or not current_time:
        return None, None

    now = datetime.fromisoformat(current_time)
    past = [
        (datetime.fromisoformat(t), v)
        for t, v in zip(times, values)
        if v is not None and datetime.fromisoformat(t) <= now
    ]
    if not past:
        return None, None

    last_24 = [v for t, v in past if (now - t).total_seconds() < 24 * 3600]
    return float(past[-1][1]), float(sum(last_24))


def parse_location_payload(location: dict, payload: dict) -> dict:
    """Convert one Open-Meteo location result into a LUVIA raw observation row."""
    current = payload.get("current")
    if not current:
        raise ValueError(f"No current weather returned for {location['location_name']}.")

    rain_1h, rain_24h = _rain_totals(payload.get("hourly") or {}, current.get("time"))

    readings = {
        "temp_c": current.get("temperature_2m"),
        "gust_kmh": current.get("wind_gusts_10m"),
        "weather_code": current.get("weather_code"),
        "rain_1h_mm": rain_1h,
        "rain_24h_mm": rain_24h,
    }

    return {
        # Requested with timezone=GMT, so the naive timestamp is UTC.
        "timestamp": f"{current['time']}+00:00",
        "location_name": location["location_name"],
        "state": location.get("state"),
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "temperature": current.get("temperature_2m"),
        "humidity": current.get("relative_humidity_2m"),
        # Current-interval precipitation (Open-Meteo's 15-minute value).
        "rainfall": current.get("precipitation"),
        "source": "OPEN_METEO",
        "readings": {k: v for k, v in readings.items() if v is not None},
        "raw": {"current": current, "rain_1h_mm": rain_1h, "rain_24h_mm": rain_24h},
    }


def fetch_india_weather(locations=None):
    """Fetch snapshots for all locations, continuing after individual failures.

    Returns ``(rows, failures)``.
    """
    locations = list(locations or INDIAN_LOCATIONS)
    rows, failures = [], []

    for start in range(0, len(locations), BATCH_SIZE):
        batch = locations[start:start + BATCH_SIZE]
        params = {
            "latitude": ",".join(str(loc["latitude"]) for loc in batch),
            "longitude": ",".join(str(loc["longitude"]) for loc in batch),
            "current": CURRENT_FIELDS,
            "hourly": "precipitation",
            "past_hours": 24,
            "forecast_hours": 1,
            "timezone": "GMT",
        }

        try:
            payload = _request_json(params)
        except Exception as exc:  # network / HTTP / JSON errors fail the whole batch
            failures.extend(
                {"location": loc["location_name"], "error": str(exc)} for loc in batch
            )
            continue

        # A single location returns an object; several return a list.
        results = payload if isinstance(payload, list) else [payload]

        for location, result in zip(batch, results):
            try:
                rows.append(parse_location_payload(location, result))
            except Exception as exc:
                failures.append({"location": location["location_name"], "error": str(exc)})

    return rows, failures


if __name__ == "__main__":
    snapshots, problems = fetch_india_weather()
    print(f"Successful snapshots: {len(snapshots)}")
    print(f"Failed locations: {len(problems)}")
    print(json.dumps(snapshots[:2], indent=2))
