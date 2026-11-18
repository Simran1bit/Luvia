"""
LUVIA severity + verification engine.  Pure Python, no database, no network.

Put this file at:  backend/app/ai/severity.py

WHY THIS EXISTS
---------------
Hourly weather observations are *measurements*, not incidents.  Labelling all of
them "low / unverified" (what the dashboard shows today) throws away the signal.
This module turns a measurement into an explainable decision:

    readings (Open-Meteo)  ->  hazards (rain / heat / cold / wind / thunder / snow)
    hazards + IMD district warning  ->  severity, verification_status, confidence

SEVERITY (per hazard, official IMD thresholds where they exist)
---------------------------------------------------------------
Rain, 24 h total   : >=64.5 mm Heavy (medium) | >=115.6 Very heavy (high) | >=204.5 Extremely heavy (critical)
                     (IMD rainfall categories)
Rain, 1 h intensity: >=30 mm/h medium | >=50 mm/h high (AMS "violent" rain) | >=100 mm/h critical
                     (100 mm/h is the IMD cloudburst definition). Engineering heuristic - tune freely.
Heat (air temp)    : >=40 C medium | >=45 C high (IMD heat-wave, absolute) | >=47 C critical (severe heat wave)
                     IMD also uses departure-from-normal; without climatology we flag, we do not over-claim.
Cold (air temp)    : <=4 C medium (IMD cold-wave, plains) | <=2 C high (severe)
Wind gust (km/h)   : >=62 medium (Beaufort 8 gale) | >=89 high (Beaufort 10 storm) | >=118 critical (Beaufort 12)
WMO weather code   : 95 thunderstorm = medium | 96/99 thunderstorm with hail, 82 violent showers,
                     67 heavy freezing rain = high | 65 heavy rain, 75/86 heavy snow = medium

VERIFICATION (explainable, two-source rule)
-------------------------------------------
verified      = an IMD district warning of Alert/Warning level (orange/red) is active TODAY
                AND the measured hazard in the SAME family (rain/heat/...) is at least medium.
                Two independent sources agree -> verified.
needs_review  = high/critical severity that has NOT been corroborated, or an official
                orange/red IMD warning with no matching measurement, or a measurement
                that matches a yellow IMD watch.  A human should look at these.
unverified    = everything else (normal observations).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Iterable

SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}
RANK_SEVERITY = {v: k for k, v in SEVERITY_RANK.items()}

# IMD color_code (feed order): 1 green / no warning, 2 yellow, 3 orange, 4 red
IMD_COLOR_SEVERITY = {1: "low", 2: "medium", 3: "high", 4: "critical"}

# IMD warning_code -> hazard family (see imdWarningService.js for the code list)
IMD_CODE_FAMILY = {
    2: "rain", 16: "rain", 17: "rain",
    3: "snow",
    4: "thunder", 5: "thunder",
    6: "wind", 7: "wind", 8: "wind",
    9: "heat", 10: "heat", 11: "heat",
    12: "cold", 13: "cold", 14: "cold",
    15: "fog",
}

# WMO weather codes (Open-Meteo `weather_code`)
WMO_HAZARDS = {
    65: ("rain", "medium", "WMO 65 heavy rain"),
    67: ("rain", "high", "WMO 67 heavy freezing rain"),
    75: ("snow", "medium", "WMO 75 heavy snowfall"),
    82: ("rain", "high", "WMO 82 violent rain showers"),
    86: ("snow", "medium", "WMO 86 heavy snow showers"),
    95: ("thunder", "medium", "WMO 95 thunderstorm"),
    96: ("thunder", "high", "WMO 96 thunderstorm with hail"),
    99: ("thunder", "high", "WMO 99 thunderstorm with heavy hail"),
}

# (threshold, severity) pairs, checked from highest to lowest.
RAIN_24H = [(204.5, "critical"), (115.6, "high"), (64.5, "medium")]
RAIN_1H = [(100.0, "critical"), (50.0, "high"), (30.0, "medium")]
HEAT = [(47.0, "critical"), (45.0, "high"), (40.0, "medium")]
COLD = [(2.0, "high"), (4.0, "medium")]  # <= comparisons, checked lowest first
GUST = [(118.0, "critical"), (89.0, "high"), (62.0, "medium")]


@dataclass
class Hazard:
    family: str
    severity: str
    reason: str


@dataclass
class Decision:
    severity: str = "low"
    status: str = "unverified"
    confidence: float | None = None
    reasons: list[str] = field(default_factory=list)
    hazards: list[Hazard] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 1) readings -> hazards
# ---------------------------------------------------------------------------
def _ge(value: float | None, table: list[tuple[float, str]]) -> str | None:
    if value is None:
        return None
    for threshold, sev in table:
        if value >= threshold:
            return sev
    return None


def classify_readings(readings: dict[str, float | int | None]) -> list[Hazard]:
    """readings keys: rain_24h_mm, rain_1h_mm, temp_c, gust_kmh, weather_code."""
    hazards: list[Hazard] = []

    sev = _ge(readings.get("rain_24h_mm"), RAIN_24H)
    if sev:
        hazards.append(Hazard("rain", sev, f"24h rainfall {readings['rain_24h_mm']:.1f} mm (IMD {sev})"))

    sev = _ge(readings.get("rain_1h_mm"), RAIN_1H)
    if sev:
        hazards.append(Hazard("rain", sev, f"rain intensity {readings['rain_1h_mm']:.1f} mm/h"))

    t = readings.get("temp_c")
    sev = _ge(t, HEAT)
    if sev:
        hazards.append(Hazard("heat", sev, f"air temperature {t:.1f} C"))
    if t is not None:
        for threshold, sev_c in COLD:  # lowest threshold first
            if t <= threshold:
                hazards.append(Hazard("cold", sev_c, f"air temperature {t:.1f} C (cold-wave range)"))
                break

    g = readings.get("gust_kmh")
    sev = _ge(g, GUST)
    if sev:
        hazards.append(Hazard("wind", sev, f"wind gust {g:.0f} km/h"))

    code = readings.get("weather_code")
    if code is not None and int(code) in WMO_HAZARDS:
        fam, sev, why = WMO_HAZARDS[int(code)]
        hazards.append(Hazard(fam, sev, why))

    return hazards


def worst(hazards: Iterable[Hazard]) -> str:
    r = max((SEVERITY_RANK[h.severity] for h in hazards), default=1)
    return RANK_SEVERITY[r]


# ---------------------------------------------------------------------------
# 2) readings + IMD -> decision
# ---------------------------------------------------------------------------
@dataclass
class ImdAlert:
    district: str
    color_code: int  # 1..4
    families: set[str]
    types: list[str] = field(default_factory=list)


def decide(readings: dict, imd: ImdAlert | None, existing_severity: str | None = None) -> Decision:
    hazards = classify_readings(readings)
    obs_sev = worst(hazards)
    d = Decision(hazards=hazards, reasons=[h.reason for h in hazards])

    imd_rank = SEVERITY_RANK[IMD_COLOR_SEVERITY.get(imd.color_code, "low")] if imd else 1
    imd_strong = bool(imd) and imd.color_code >= 3  # orange / red
    imd_watch = bool(imd) and imd.color_code == 2   # yellow

    if imd and imd.color_code >= 2:
        d.reasons.append(
            f"IMD {['', 'green', 'yellow', 'orange', 'red'][imd.color_code]} for {imd.district} today"
            + (f": {', '.join(imd.types)}" if imd.types else "")
        )

    matching = [h for h in hazards if imd and h.family in imd.families]
    matching_medium = any(SEVERITY_RANK[h.severity] >= 2 for h in matching)

    final_rank = max(SEVERITY_RANK[obs_sev], imd_rank if (imd_strong or imd_watch) else 1)
    if existing_severity in SEVERITY_RANK:  # never downgrade a better classification
        final_rank = max(final_rank, SEVERITY_RANK[existing_severity])
    d.severity = RANK_SEVERITY[final_rank]

    if imd_strong and matching_medium:
        d.status = "verified"
        d.confidence = 0.9 if SEVERITY_RANK[obs_sev] >= 3 else 0.8
        d.reasons.append("Measurement and official IMD warning agree (two independent sources)")
    elif final_rank >= 3:
        d.status = "needs_review"
        d.confidence = 0.6 if imd_strong else 0.5
        d.reasons.append(
            "Official IMD warning without a matching measurement" if imd_strong
            else "High-severity measurement without IMD corroboration"
        )
    elif matching_medium and imd_watch:
        d.status = "needs_review"
        d.confidence = 0.45
        d.reasons.append("Measurement matches an IMD yellow watch")
    else:
        d.status = "unverified"
        d.confidence = 0.35 if final_rank == 2 else None
    return d


# ---------------------------------------------------------------------------
# 3) tolerant reading extraction (unknown storage format)
# ---------------------------------------------------------------------------
_ALIASES = {
    "rain_24h_mm": ["rain_24h", "precipitation_24h", "precipitation_sum", "rain_sum", "rainfall_24h",
                    "daily_precipitation", "rain_24h_mm", "precip_24h"],
    "rain_1h_mm": ["precipitation", "rain", "rainfall", "precip", "precipitation_mm", "rain_mm",
                   "rainfall_mm", "precipitation_1h", "rain_1h", "precipitation_mm_h"],
    "temp_c": ["temperature_2m", "temperature", "temp", "temp_c", "temperature_c", "temperature_2m_max",
               "temp_max"],
    "gust_kmh": ["wind_gusts_10m", "wind_gusts", "wind_gust", "gust", "gust_kmh", "windgusts", "wind_gusts_kmh"],
    "weather_code": ["weather_code", "weathercode", "wmo_code", "weather_code_wmo"],
}
_LOOKUP = {alias: canon for canon, aliases in _ALIASES.items() for alias in aliases}

_TEXT_PATTERNS = {
    "rain_24h_mm": r"(?:24\s*h(?:our)?s?\s*(?:rain(?:fall)?|precip\w*)|daily\s*(?:rain(?:fall)?|precip\w*))\D{0,12}(-?\d+(?:\.\d+)?)\s*mm",
    "rain_1h_mm": r"(?:rain(?:fall)?|precip\w*)\D{0,12}(-?\d+(?:\.\d+)?)\s*mm",
    "temp_c": r"temp\w*\D{0,12}(-?\d+(?:\.\d+)?)\s*(?:°|º|deg\w*)?\s*c\b",
    "gust_kmh": r"gust\w*\D{0,12}(-?\d+(?:\.\d+)?)\s*(?:km/?h|kph)",
    "weather_code": r"weather[_ ]?code\D{0,6}(\d{1,2})",
}


def _walk(obj: Any, out: dict, depth: int = 0) -> None:
    if depth > 6:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            canon = _LOOKUP.get(str(k).lower())
            if canon and canon not in out:
                # Open-Meteo daily values are short arrays (e.g. precipitation_sum: [12.3]); take the max.
                # Long (hourly) arrays are skipped on purpose - they are not one observation.
                if isinstance(v, list) and 0 < len(v) <= 7 and all(isinstance(x, (int, float)) for x in v if x is not None):
                    nums = [x for x in v if x is not None]
                    if nums:
                        out[canon] = float(max(nums))
                else:
                    try:
                        if isinstance(v, (int, float)) and not isinstance(v, bool) or (
                            isinstance(v, str) and re.fullmatch(r"-?\d+(\.\d+)?", v.strip())
                        ):
                            out[canon] = float(v)
                    except (TypeError, ValueError):
                        pass
            _walk(v, out, depth + 1)
    elif isinstance(obj, list):
        for v in obj[:50]:
            _walk(v, out, depth + 1)
    elif isinstance(obj, str):
        s = obj.strip()
        if s[:1] in "{[" and len(s) < 200_000:
            try:
                _walk(json.loads(s), out, depth + 1)
            except ValueError:
                pass


def extract_readings(*blobs: Any) -> dict[str, float]:
    """Find weather readings in dicts / JSON strings / free text (first match wins per key)."""
    out: dict[str, float] = {}
    for b in blobs:
        if b is None:
            continue
        _walk(b, out)
    for b in blobs:
        if isinstance(b, str):
            low = b.lower()
            for canon, pat in _TEXT_PATTERNS.items():  # order matters: 24h pattern runs first
                if canon in out:
                    continue
                m = re.search(pat, low)
                if m:
                    try:
                        out[canon] = float(m.group(1))
                    except ValueError:
                        continue
                    # blank out the matched span so "24h rainfall 131 mm" is not re-read as hourly rain
                    low = low[:m.start()] + " " * (m.end() - m.start()) + low[m.end():]
    return out
