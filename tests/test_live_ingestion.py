"""Offline tests for the live ingestion adapters and assessment step.

Fixtures in tests/fixtures/ are trimmed copies of real responses from
aviationweather.gov, NDMA SACHET and Open-Meteo. No network or database
access happens here.
"""

import json
from pathlib import Path

import pytest

from backend.app.ai.severity import decide
from backend.app.ingestion.adapters.metar_adapter import (
    latest_by_station, parse_metar, relative_humidity, weather_code_from_wx,
)
from backend.app.ingestion.adapters.open_meteo_adapter import parse_location_payload
from backend.app.ingestion.adapters.sachet_adapter import parse_cap, parse_rss
from backend.app.ingestion.live_pipeline import assess
from backend.app.ingestion.locations import INDIAN_LOCATIONS, find_location
from backend.app.services.imd_matching import (
    build_imd_index, feed_color_to_level, find_alert,
)

FIXTURES = Path(__file__).parent / "fixtures"
MUMBAI = find_location("Mumbai")
DELHI = find_location("New Delhi")


def load_json(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def imd_warning(district, feed_colour, codes):
    """An IMD district-warning record shaped like the stored/API rows."""
    return {"district": district, "state": "", "days": [
        {"day": 1, "warning_code": codes, "color_code": feed_colour},
    ]}


# ---- registry ---------------------------------------------------------------

def test_registry_has_about_fifty_unique_cities():
    names = [loc["location_name"] for loc in INDIAN_LOCATIONS]
    assert len(names) >= 50
    assert len(names) == len(set(names))
    assert all(loc["imd_district"] for loc in INDIAN_LOCATIONS)


# ---- METAR ------------------------------------------------------------------

@pytest.mark.parametrize("wx, code", [
    ("+TSRA", 95), ("TSGR", 96), ("+SHRA", 82), ("+RA", 65), ("-RA", 63),
    ("HZ", None), ("FU", None), (None, None), ("BR FG", 45),
])
def test_weather_code_from_wx(wx, code):
    assert weather_code_from_wx(wx) == code


def test_relative_humidity_from_dewpoint():
    assert relative_humidity(17, 10) == pytest.approx(63.4, abs=1)
    assert relative_humidity(20, 20) == 100.0
    assert relative_humidity(None, 10) is None


def test_latest_metar_per_station_and_parse():
    latest = latest_by_station(load_json("metar_sample.json"))
    assert set(latest) == {"VIDP", "VABB"}
    assert latest["VIDP"]["obsTime"] == 1795806000

    row = parse_metar(latest["VABB"], MUMBAI)
    assert row["source"] == "METAR"
    assert row["location_name"] == "Mumbai"
    assert row["timestamp"].startswith("2026-11-27T19:00:00")
    assert row["rainfall"] is None
    assert row["readings"]["gust_kmh"] == pytest.approx(70.4, abs=0.1)  # 38 kt
    assert row["readings"]["weather_code"] == 95
    assert row["raw"]["raw_metar"].startswith("METAR VABB")


# ---- SACHET -----------------------------------------------------------------

def test_parse_sachet_rss_skips_items_without_guid():
    items = parse_rss((FIXTURES / "sachet_rss_sample.xml").read_bytes())
    assert len(items) == 1
    assert items[0]["identifier"] == "1795797952848041"
    assert items[0]["published_at"].startswith("2026-11-27T16:48:17")


def test_parse_sachet_cap_maps_severity_and_area():
    alert = parse_cap((FIXTURES / "sachet_cap_sample.xml").read_bytes())
    assert alert["event"] == "Light Rain"
    assert alert["cap_severity"] == "Moderate"
    assert alert["severity"] == "medium"
    assert alert["expires_at"] == "2026-11-28T01:00:00+05:30"
    assert "Pondicherry" in alert["area"]
    assert alert["district_codes"] == ["598", "600"]


# ---- Open-Meteo -------------------------------------------------------------

def test_open_meteo_rain_totals_exclude_forecast_hours():
    row = parse_location_payload(MUMBAI, load_json("open_meteo_sample.json"))
    readings = row["readings"]
    assert row["timestamp"] == "2026-11-27T19:00+00:00"
    assert readings["rain_1h_mm"] == 20.0
    # 26T20 + 27T18 + 27T19; the 24h-old hour and the future 27T20 are excluded.
    assert readings["rain_24h_mm"] == 70.0
    assert readings["gust_kmh"] == 70.5
    assert readings["weather_code"] == 65


# ---- IMD matching -----------------------------------------------------------

def test_imd_feed_colours_are_inverted():
    assert feed_color_to_level(4) == 1  # green / no warning
    assert feed_color_to_level(3) == 2  # yellow
    assert feed_color_to_level(1) == 4  # red
    assert feed_color_to_level(0) is None


def test_no_warning_districts_are_not_indexed():
    index = build_imd_index([
        imd_warning("NEW DELHI", 4, "1"),            # green, no warning
        imd_warning("MUMBAI CITY", 2, "2,4"),        # orange: heavy rain + thunderstorm
    ])
    assert find_alert(index, "New Delhi", "Delhi", "NEW DELHI") is None

    alert = find_alert(index, "Mumbai", "Maharashtra", "MUMBAI CITY")
    assert alert.color_code == 3
    assert alert.families == {"rain", "thunder"}


def test_city_falls_back_to_fuzzy_district_match():
    index = build_imd_index([imd_warning("MUMBAI SUBURBAN", 3, "15")])
    alert = find_alert(index, "Mumbai", None)
    assert alert is not None and alert.color_code == 2


# ---- assessment -------------------------------------------------------------

def test_assess_verifies_when_measurement_and_imd_agree():
    row = parse_location_payload(MUMBAI, load_json("open_meteo_sample.json"))
    index = build_imd_index([imd_warning("MUMBAI CITY", 2, "2")])  # orange heavy rain

    event = assess(row, index)

    assert event["event_type"] == "heavy_rainfall"
    assert event["title"].startswith("Heavy rainfall — Mumbai")
    assert event["severity"] in ("medium", "high")
    assert event["verification_status"] == "verified"
    assert event["credibility_score"] >= 0.8
    assert any("IMD orange" in reason for reason in event["risk_reasons"])


def test_assess_yellow_watch_alone_is_not_verified():
    row = parse_location_payload(DELHI, {
        "current": {"time": "2026-11-27T19:00", "temperature_2m": 17, "relative_humidity_2m": 60,
                    "precipitation": 0.0, "weather_code": 0, "wind_gusts_10m": 5},
        "hourly": {},
    })
    index = build_imd_index([imd_warning("NEW DELHI", 3, "15")])  # yellow fog watch

    event = assess(row, index)

    assert event["event_type"] == "weather_observation"
    assert event["verification_status"] == "unverified"
    assert event["severity"] == "medium"  # raised by the IMD watch, not invented


def test_decide_without_imd_flags_high_severity_for_review():
    decision = decide({"rain_24h_mm": 130.0}, None)
    assert decision.severity == "high"
    assert decision.status == "needs_review"
