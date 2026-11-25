"""Centralized, read-only access to LUVIA's DB and Open-Meteo.

DB discovery is deliberately conservative: inspect table/column names, then
read only recognized event/warning tables. Set LUVIA_CHAT_EVENT_TABLE and
LUVIA_CHAT_WARNING_TABLE to override discovery for your schema.
"""
from __future__ import annotations
import os
from datetime import datetime, timezone
from typing import Any
import requests
from .config import DATABASE_URL, OPEN_METEO_URL, GEOCODING_URL, REQUEST_TIMEOUT

EVENT_NAMES = ("weather_events", "events", "historical_events", "weather_event")
WARNING_NAMES = ("imd_warnings", "warnings", "weather_warnings", "alerts")

def _engine():
    if not DATABASE_URL:
        return None
    try:
        from sqlalchemy import create_engine
        return create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
    except Exception:
        return None

def _tables(engine):
    from sqlalchemy import inspect
    return inspect(engine).get_table_names()

def _read_table(table: str, limit: int = 100):
    engine = _engine()
    if engine is None:
        return [], "Database is not configured (DATABASE_URL)."
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        if table not in inspector.get_table_names():
            return [], f"Table '{table}' was not found."
        # Table name comes only from introspection or explicit environment config.
        cols = [c["name"] for c in inspector.get_columns(table)]
        allowed = '"' + table.replace('"', '""') + '"'
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT * FROM {allowed} LIMIT :lim"), {"lim": limit})
            rows = [dict(r._mapping) for r in result]
        return rows, None
    except Exception as exc:
        return [], f"Could not read {table}: {type(exc).__name__}: {exc}"

def _choose_table(names, candidates, override):
    if override:
        return override
    lower = {n.lower(): n for n in names}
    for candidate in candidates:
        if candidate in lower:
            return lower[candidate]
    return None

def get_events(location: str | None = None, category: str | None = None, limit: int = 50):
    engine = _engine()
    if engine is None:
        return {"records": [], "source": "LUVIA database", "error": "DATABASE_URL is not configured."}
    try:
        names = _tables(engine)
        table = _choose_table(names, EVENT_NAMES, os.getenv("LUVIA_CHAT_EVENT_TABLE"))
        if not table:
            return {"records": [], "source": "LUVIA database", "error": "No recognized event table found. Set LUVIA_CHAT_EVENT_TABLE to your event table name."}
        rows, error = _read_table(table, min(max(limit, 1), 200))
        if error: return {"records": [], "source": table, "error": error}
        def match(row):
            values = " ".join(str(v) for v in row.values() if v is not None).lower()
            return (not location or location.lower() in values) and (not category or category.lower() in values)
        selected = [r for r in rows if match(r)]
        return {"records": selected[:limit], "source": table, "count": len(selected), "checked_at": datetime.now(timezone.utc).isoformat()}
    except Exception as exc:
        return {"records": [], "source": "LUVIA database", "error": str(exc)}

def get_warnings(location: str | None = None, limit: int = 50):
    engine = _engine()
    if engine is None:
        return {"records": [], "source": "LUVIA database", "error": "DATABASE_URL is not configured; warning status cannot be confirmed."}
    try:
        table = _choose_table(_tables(engine), WARNING_NAMES, os.getenv("LUVIA_CHAT_WARNING_TABLE"))
        if not table:
            return {"records": [], "source": "LUVIA database", "error": "No recognized warning table found; warning status cannot be confirmed."}
        rows, error = _read_table(table, min(max(limit, 1), 200))
        if error: return {"records": [], "source": table, "error": error}
        rows = [r for r in rows if not location or location.lower() in " ".join(str(v) for v in r.values() if v is not None).lower()]
        return {"records": rows[:limit], "source": table, "count": len(rows), "checked_at": datetime.now(timezone.utc).isoformat()}
    except Exception as exc:
        return {"records": [], "source": "LUVIA database", "error": f"Warning status cannot be confirmed: {exc}"}

def current_weather(location: str):
    try:
        geo = requests.get(GEOCODING_URL, params={"name": location, "count": 1, "language": "en", "format": "json"}, timeout=REQUEST_TIMEOUT)
        geo.raise_for_status(); results = geo.json().get("results") or []
        if not results: return {"error": f"I couldn't resolve the location '{location}'."}
        place = results[0]
        response = requests.get(OPEN_METEO_URL, params={"latitude": place["latitude"], "longitude": place["longitude"], "current": "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,rain,showers,weather_code,wind_speed_10m,wind_direction_10m", "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code", "forecast_days": 3, "timezone": "auto"}, timeout=REQUEST_TIMEOUT)
        response.raise_for_status(); data = response.json()
        return {"location": ", ".join(x for x in [place.get("name"), place.get("admin1"), place.get("country")] if x), "current": data.get("current"), "daily": data.get("daily"), "timezone": data.get("timezone"), "source": "Open-Meteo", "checked_at": datetime.now(timezone.utc).isoformat()}
    except Exception as exc:
        return {"error": f"Live weather could not be retrieved: {exc}", "source": "Open-Meteo"}
