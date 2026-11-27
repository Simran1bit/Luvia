"""Live ingestion pipeline: fetch -> normalise -> validate -> assess -> persist.

One function per source, each returning a summary dict, so the same code runs
from the scheduler (``services/ingestion_scheduler.py``) and the CLI
(``ingestion/run_live.py``).

Assessment uses ``backend.app.ai.severity.decide`` with the official IMD Day-1
district warning for the city, so every stored event carries a real
severity, verification status, confidence and human-readable reasons.
"""

from __future__ import annotations

import logging

from sqlalchemy import text

from backend.app.ai.severity import SEVERITY_RANK, decide
from backend.app.database import engine
from backend.app.ingestion.adapters.imd_station_adapter import fetch_imd_station_observations
from backend.app.ingestion.adapters.imd_warning_adapter import fetch_imd_district_warnings
from backend.app.ingestion.adapters.metar_adapter import fetch_metar_observations
from backend.app.ingestion.adapters.open_meteo_adapter import fetch_india_weather
from backend.app.ingestion.adapters.sachet_adapter import fetch_sachet_alerts
from backend.app.ingestion.locations import find_location
from backend.app.ingestion.normalizer import normalize_weather_event
from backend.app.ingestion.validator import validate_weather_event
from backend.app.services.event_persistence import (
    attach_source, find_event_near, find_existing, save_event, update_assessment,
)
from backend.app.services.imd_matching import find_alert, load_imd_index_from_db
from backend.app.services.imd_warning_persistence import save_imd_warnings
from backend.app.services.official_alert_persistence import (
    known_identifiers, save_official_alerts,
)

logger = logging.getLogger(__name__)

# Worst hazard family -> event_type shown in the dashboard's type filter.
HAZARD_EVENT_TYPES = {
    "rain": "heavy_rainfall",
    "heat": "heat",
    "cold": "cold_wave",
    "wind": "strong_wind",
    "thunder": "thunderstorm",
    "snow": "snow",
}
HAZARD_TITLES = {
    "heavy_rainfall": "Heavy rainfall",
    "heat": "High temperature",
    "cold_wave": "Cold conditions",
    "strong_wind": "Strong wind",
    "thunderstorm": "Thunderstorm",
    "snow": "Snowfall",
}
STATUS_RANK = {"unverified": 0, "needs_review": 1, "verified": 2}


def _summary(source, fetched=0, failures=(), **counts):
    return {"source": source, "fetched": fetched, "failures": list(failures), **counts}


def _load_imd_index():
    """IMD alerts from the database; ingestion continues without them if unavailable."""
    try:
        with engine.connect() as connection:
            return load_imd_index_from_db(connection)
    except Exception:
        logger.exception("Could not load IMD warnings; continuing without IMD corroboration.")
        return {}


def assess(row: dict, imd_index: dict) -> dict:
    """Normalise one raw observation and attach the severity/verification decision."""
    event = normalize_weather_event(row)
    event["readings"] = row.get("readings") or {}
    event["raw"] = row.get("raw")

    location = event["location"]
    registry = find_location(location["name"]) or {}
    alert = find_alert(
        imd_index, location["name"], location.get("state"), registry.get("imd_district")
    )
    decision = decide(event["readings"], alert)

    worst = max(decision.hazards, key=lambda h: SEVERITY_RANK[h.severity], default=None)
    event_type = HAZARD_EVENT_TYPES.get(worst.family) if worst else None

    station = row.get("station")
    label = f"{location['name']} ({station})" if station else location["name"]

    event.update({
        "event_type": event_type or "weather_observation",
        "title": f"{HAZARD_TITLES.get(event_type, 'Weather observation')} — {label}",
        "severity": decision.severity,
        "verification_status": decision.status,
        "credibility_score": decision.confidence,
        "risk_reasons": decision.reasons,
        "hazard_families": sorted({h.family for h in decision.hazards}),
        # Measurement-only reasons (no IMD text), used when merging sources.
        "hazard_reasons": [h.reason for h in decision.hazards],
    })
    return event


def _ingest_observations(source, rows, failures, required, imd_index=None):
    """Shared path for sources that each produce their own event per city."""
    imd_index = _load_imd_index() if imd_index is None else imd_index
    saved = skipped = invalid = 0
    failures = list(failures)

    for row in rows:
        try:
            event = assess(row, imd_index)
            valid, errors = validate_weather_event(event, required=required)
            if not valid:
                invalid += 1
                failures.append({"location": row.get("location_name"), "error": "; ".join(errors)})
                continue

            location = event["location"]
            with engine.begin() as connection:
                if find_existing(connection, event["source"], event["timestamp"],
                                 location["latitude"], location["longitude"]):
                    skipped += 1
                    continue
                save_event(event, connection)
                saved += 1
        except Exception as exc:
            failures.append({"location": row.get("location_name"), "error": str(exc)})

    return _summary(source, len(rows), failures, saved=saved, skipped=skipped, invalid=invalid)


def ingest_open_meteo():
    rows, failures = fetch_india_weather()
    return _ingest_observations(
        "OPEN_METEO", rows, failures, required=("temperature", "humidity", "rainfall")
    )


def ingest_imd_stations():
    rows, failures = fetch_imd_station_observations()
    if not rows and not failures:
        return _summary("IMD_STATION", status="disabled")
    return _ingest_observations("IMD_STATION", rows, failures, required=("temperature",))


def _merge_into_event(connection, event_id: int, metar_event: dict) -> None:
    """Combine a METAR assessment with the Open-Meteo event it corroborates.

    Severity and status take the stronger of the two assessments. When both
    sources independently show the same hazard family, that agreement is
    recorded as a reason.
    """
    current = connection.execute(
        text("""
            SELECT event_type, severity, verification_status, credibility_score, risk_reasons
            FROM events WHERE event_id = :event_id
        """),
        {"event_id": event_id},
    ).mappings().one()

    severity = current["severity"]
    if SEVERITY_RANK.get(metar_event["severity"], 0) > SEVERITY_RANK.get(severity, 0):
        severity = metar_event["severity"]

    status = current["verification_status"]
    if STATUS_RANK.get(metar_event["verification_status"], 0) > STATUS_RANK.get(status, 0):
        status = metar_event["verification_status"]

    confidences = [c for c in (current["credibility_score"], metar_event["credibility_score"]) if c is not None]
    confidence = max((float(c) for c in confidences), default=None)

    station = (metar_event.get("raw") or {}).get("icao", "airport")
    reasons = list(current["risk_reasons"] or [])
    # The IMD part of the reasons is already on the event; add only what the airport measured.
    reasons += [f"METAR {station}: {reason}" for reason in metar_event["hazard_reasons"]]

    om_type = current["event_type"]
    metar_types = {HAZARD_EVENT_TYPES[f] for f in metar_event["hazard_families"] if f in HAZARD_EVENT_TYPES}
    if om_type in metar_types:
        reasons.append(
            f"Airport observation ({station}) independently shows the same hazard as the model data"
        )

    update_assessment(connection, event_id, severity, status, confidence, reasons)


def ingest_metar():
    """Attach METARs to the matching Open-Meteo event, or store them on their own."""
    rows, failures = fetch_metar_observations()
    imd_index = _load_imd_index()
    attached = standalone = skipped = invalid = 0
    failures = list(failures)

    for row in rows:
        try:
            event = assess(row, imd_index)
            valid, errors = validate_weather_event(event, required=("temperature",))
            if not valid:
                invalid += 1
                failures.append({"location": row.get("location_name"), "error": "; ".join(errors)})
                continue

            location = event["location"]
            with engine.begin() as connection:
                if find_existing(connection, "METAR", event["timestamp"],
                                 location["latitude"], location["longitude"]):
                    skipped += 1
                    continue

                near = find_event_near(connection, location["name"], event["timestamp"])
                if near:
                    attach_source(connection, near, event)
                    _merge_into_event(connection, near, event)
                    attached += 1
                else:
                    save_event(event, connection)
                    standalone += 1
        except Exception as exc:
            failures.append({"location": row.get("location_name"), "error": str(exc)})

    return _summary(
        "METAR", len(rows), failures,
        attached=attached, standalone=standalone, skipped=skipped, invalid=invalid,
    )


def ingest_imd_warnings():
    records = fetch_imd_district_warnings()
    result = save_imd_warnings(records)
    return _summary("IMD_WARNINGS", len(records), **result)


def ingest_sachet():
    with engine.connect() as connection:
        known = known_identifiers(connection)
    alerts, failures = fetch_sachet_alerts(known_identifiers=known)
    result = save_official_alerts(alerts) if alerts else {"saved": 0}
    return _summary("SACHET", len(alerts), failures, already_stored=len(known), **result)


def ingest_observations():
    """Open-Meteo then METAR, in sequence, so METARs can attach to fresh model events.

    Running them as separate scheduled jobs let METAR start before the
    Open-Meteo rows were saved, which created duplicate standalone events.
    """
    om = ingest_open_meteo()
    metar = ingest_metar()
    return _summary(
        "OBSERVATIONS",
        om["fetched"] + metar["fetched"],
        om["failures"] + metar["failures"],
        open_meteo={k: v for k, v in om.items() if k not in ("source", "failures")},
        metar={k: v for k, v in metar.items() if k not in ("source", "failures")},
    )


INGESTORS = {
    "imd_warnings": ingest_imd_warnings,
    "observations": ingest_observations,
    "openmeteo": ingest_open_meteo,
    "metar": ingest_metar,
    "sachet": ingest_sachet,
    "imd_station": ingest_imd_stations,
}
