"""Match LUVIA locations to official IMD district warnings.

Shared by the live ingestion pipeline and ``run_enrich_events.py`` so the
matching rules live in one place.

Two facts about the IMD district-warning feed (checked against live data):

1. **The colour scale is inverted** relative to the usual green->red order:
   feed ``4`` = green / no warning, ``3`` = yellow, ``2`` = orange, ``1`` = red.
   (Every district whose warning code is "1 - No Warning" carries colour 4.)
   ``feed_color_to_level`` converts it to an *alert level* 1..4
   (green, yellow, orange, red), which is what ``severity.ImdAlert`` expects.
2. **The ``state`` field is empty** for almost every district, so warnings are
   matched by district name, not grouped by state.
"""

from __future__ import annotations

import re
import unicodedata

from sqlalchemy import text

from backend.app.ai.severity import IMD_CODE_FAMILY, ImdAlert

# Feed colour code -> alert level (1 green, 2 yellow, 3 orange, 4 red).
FEED_COLOR_TO_LEVEL = {4: 1, 3: 2, 2: 3, 1: 4}

IMD_CODE_NAME = {
    2: "Heavy Rain", 3: "Heavy Snow", 4: "Thunderstorm & Lightning", 5: "Hailstorm",
    6: "Dust Storm", 7: "Dust Raising Winds", 8: "Strong Surface Winds", 9: "Heat Wave",
    10: "Hot Day", 11: "Warm Night", 12: "Cold Wave", 13: "Cold Day", 14: "Ground Frost",
    15: "Fog", 16: "Very Heavy Rain", 17: "Extremely Heavy Rain",
}

CITY_ALIASES = {
    "bangalore": "bengaluru", "banglore": "bengaluru", "bombay": "mumbai", "calcutta": "kolkata",
    "madras": "chennai", "gurgaon": "gurugram", "trivandrum": "thiruvananthapuram",
    "cochin": "kochi", "allahabad": "prayagraj", "poona": "pune", "baroda": "vadodara",
    "banaras": "varanasi", "benares": "varanasi", "mysore": "mysuru", "new delhi": "delhi",
    "khurda": "khordha", "ahmadabad": "ahmedabad",
}
STATE_ALIASES = {
    "orissa": "odisha", "odhisha": "odisha", "uttaranchal": "uttarakhand",
    "nct of delhi": "delhi", "delhi nct": "delhi",
    "jammu and kashmir": "jammu kashmir", "pondicherry": "puducherry",
}
_DROP = re.compile(r"\b(district|dist|city|urban|rural|metropolitan|municipal corporation)\b")


def _clean(value) -> str:
    s = unicodedata.normalize("NFKD", str(value or "").lower())
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).replace("&", " and ")
    s = _DROP.sub(" ", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def norm_city(value) -> str:
    c = _clean(value)
    return CITY_ALIASES.get(c, c)


def norm_state(value) -> str:
    c = _clean(value)
    return STATE_ALIASES.get(c, c)


def district_matches_city(district_norm: str, city_norm: str) -> bool:
    if not district_norm or not city_norm:
        return False
    if district_norm == city_norm:
        return True
    return city_norm in district_norm.split(" ") or district_norm.startswith(city_norm + " ")


def feed_color_to_level(color) -> int | None:
    """Convert an IMD feed colour code to an alert level (1 green .. 4 red)."""
    try:
        return FEED_COLOR_TO_LEVEL.get(int(color))
    except (TypeError, ValueError):
        return None


def _day_one(days: list[dict]) -> dict | None:
    return next(
        (d for d in days if re.sub(r"\D", "", str(d.get("day", ""))) == "1"),
        days[0] if days else None,
    )


def build_imd_index(warnings: list[dict]) -> dict[str, ImdAlert]:
    """Index real Day-1 warnings (yellow or worse) by normalised district name."""
    index: dict[str, ImdAlert] = {}

    for warning in warnings:
        day1 = _day_one(warning.get("days") or [])
        if not day1:
            continue

        level = feed_color_to_level(day1.get("color_code"))
        codes = [
            int(c) for c in re.findall(r"\d+", str(day1.get("warning_code", ""))) if int(c) != 1
        ]
        if level is None or level < 2 or not codes:
            continue

        district = (warning.get("district") or "").strip()
        alert = ImdAlert(
            district=district.title(),
            color_code=level,
            families={IMD_CODE_FAMILY[c] for c in codes if c in IMD_CODE_FAMILY},
            types=[IMD_CODE_NAME.get(c, f"code {c}") for c in codes],
        )

        key = norm_city(district)
        if key and (key not in index or alert.color_code > index[key].color_code):
            index[key] = alert

    return index


def find_alert(index: dict[str, ImdAlert], city, state=None, district=None) -> ImdAlert | None:
    """Return the strongest Day-1 alert for a location, or None.

    An explicit IMD district name (from the city registry) is matched exactly;
    otherwise the city name is fuzzily matched against district names.
    ``state`` is accepted for API compatibility but the feed rarely fills it.
    """
    if district:
        alert = index.get(norm_city(district))
        if alert:
            return alert

    city_norm = norm_city(city)
    best = None
    for district_norm, alert in index.items():
        if district_matches_city(district_norm, city_norm) and (
            best is None or alert.color_code > best.color_code
        ):
            best = alert
    return best


def load_imd_index_from_db(connection) -> dict[str, ImdAlert]:
    """Build the alert index from the newest stored IMD issue date."""
    rows = connection.execute(text("""
        SELECT district, state, days
        FROM imd_district_warnings
        WHERE issue_date = (SELECT MAX(issue_date) FROM imd_district_warnings)
    """)).mappings().all()

    return build_imd_index([dict(row) for row in rows])
