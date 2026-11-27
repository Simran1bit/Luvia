"""Fetch measured airport observations (METAR) for Indian cities.

Source: NOAA Aviation Weather Center Data API (free, no key)
    https://aviationweather.gov/api/data/metar?ids=VIDP,VABB&format=json&hours=2

METARs are real instrument readings taken every 30-60 minutes at airports, so
they are independent of Open-Meteo's model-based values and can corroborate
them. METARs do not report a rainfall amount, only present-weather codes such
as ``+RA`` (heavy rain) or ``TSRA`` (thunderstorm with rain); those are mapped
onto WMO weather codes so ``severity.classify_readings`` can use them.
"""

import json
import math
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from backend.app.ingestion.locations import INDIAN_LOCATIONS

METAR_URL = "https://aviationweather.gov/api/data/metar"
USER_AGENT = "LUVIA-Weather-Intelligence/1.0"
KNOTS_TO_KMH = 1.852


def relative_humidity(temp_c, dewpoint_c):
    """Relative humidity (%) from air temperature and dewpoint (Magnus formula)."""
    if temp_c is None or dewpoint_c is None:
        return None

    def vapour(t):
        return math.exp(17.625 * t / (243.04 + t))

    return round(max(0.0, min(100.0, 100 * vapour(dewpoint_c) / vapour(temp_c))), 1)


def weather_code_from_wx(wx: str | None) -> int | None:
    """Map a METAR present-weather string to the closest WMO weather code.

    Only significant weather is mapped; haze, smoke, mist and similar
    obscurations return None because they are not weather hazards here.
    """
    if not wx:
        return None

    tokens = wx.upper().split()

    def has(fragment):
        return any(fragment in token for token in tokens)

    def heavy(fragment):
        return any(token.startswith("+") and fragment in token for token in tokens)

    if has("TS"):
        return 96 if (has("GR") or has("GS")) else 95
    if heavy("SHRA"):
        return 82
    if has("SHRA"):
        return 81
    if heavy("RA"):
        return 65
    if has("RA"):
        return 63
    if heavy("SN"):
        return 75
    if has("SN"):
        return 73
    if has("DZ"):
        return 53
    if has("FG"):
        return 45
    return None


def _to_kmh(knots):
    return round(float(knots) * KNOTS_TO_KMH, 1) if isinstance(knots, (int, float)) else None


def parse_metar(report: dict, location: dict) -> dict:
    """Convert one aviationweather.gov JSON METAR into a LUVIA raw observation row."""
    observed = datetime.fromtimestamp(int(report["obsTime"]), tz=timezone.utc)
    temp = report.get("temp")
    gust_kmh = _to_kmh(report.get("wgst"))
    code = weather_code_from_wx(report.get("wxString"))

    readings = {"temp_c": temp, "gust_kmh": gust_kmh, "weather_code": code}

    return {
        "timestamp": observed.isoformat(),
        "location_name": location["location_name"],
        "state": location.get("state"),
        # Station coordinates, not the city centre: this is where it was measured.
        "latitude": report.get("lat", location["latitude"]),
        "longitude": report.get("lon", location["longitude"]),
        "temperature": temp,
        "humidity": relative_humidity(temp, report.get("dewp")),
        "rainfall": None,  # METAR does not report a rainfall amount
        "source": "METAR",
        "station": report.get("icaoId"),
        "readings": {k: v for k, v in readings.items() if v is not None},
        "raw": {
            "icao": report.get("icaoId"),
            "station_name": report.get("name"),
            "raw_metar": report.get("rawOb"),
            "wx": report.get("wxString"),
            "wind_dir": report.get("wdir"),
            "wind_kmh": _to_kmh(report.get("wspd")),
            "gust_kmh": gust_kmh,
            "visibility_mi": report.get("visib"),
            "pressure_hpa": report.get("altim"),
            "dewpoint_c": report.get("dewp"),
        },
    }


def latest_by_station(reports: list[dict]) -> dict[str, dict]:
    """Keep only the newest report for each station."""
    latest = {}
    for report in reports:
        icao = report.get("icaoId")
        if not icao or report.get("obsTime") is None:
            continue
        if icao not in latest or report["obsTime"] > latest[icao]["obsTime"]:
            latest[icao] = report
    return latest


def fetch_metar_observations(locations=None, hours: int = 2):
    """Fetch the newest METAR for every location that has an airport.

    Returns ``(rows, failures)``.
    """
    locations = [loc for loc in (locations or INDIAN_LOCATIONS) if loc.get("metar_icao")]
    if not locations:
        return [], []

    params = {
        "ids": ",".join(loc["metar_icao"] for loc in locations),
        "format": "json",
        "hours": hours,
    }
    request = Request(f"{METAR_URL}?{urlencode(params)}", headers={"User-Agent": USER_AGENT})

    try:
        with urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8").strip()
        reports = json.loads(body) if body else []
    except Exception as exc:
        return [], [{"location": "all METAR stations", "error": str(exc)}]

    latest = latest_by_station(reports)
    rows, failures = [], []

    for location in locations:
        report = latest.get(location["metar_icao"])
        if report is None:
            failures.append({
                "location": location["location_name"],
                "error": f"no recent METAR from {location['metar_icao']}",
            })
            continue
        try:
            rows.append(parse_metar(report, location))
        except Exception as exc:
            failures.append({"location": location["location_name"], "error": str(exc)})

    return rows, failures


if __name__ == "__main__":
    observations, problems = fetch_metar_observations()
    print(f"METAR observations: {len(observations)}  failures: {len(problems)}")
    print(json.dumps(observations[:2], indent=2))
