"""
Classify stored weather events (severity + verification_status + confidence_score)
using Open-Meteo readings and today's official IMD district warnings.

Put this file at:  backend/app/ingestion/run_enrich_events.py
(needs  backend/app/ai/severity.py  from the same drop-in)

RUN (from the backend/ folder, with your venv active and the API running):

    python -m app.ingestion.run_enrich_events              # DRY RUN - changes nothing, prints a report
    python -m app.ingestion.run_enrich_events --apply      # writes to the database

Options:
    --db-url URL       default: $DATABASE_URL, else DATABASE_URL in ./.env or ../.env
    --api-base URL     default: http://127.0.0.1:8000   (used only to read /imd-warnings/)
    --events-table N   default: events
    --limit N          only look at the newest N rows (handy for a first test)

SAFETY
  * Dry run by default.
  * Rows already 'verified' or 'rejected' (human decisions) are never touched.
  * Severity is never lowered, 'needs_review'/'pending' is never reset to 'unverified'.
  * Only columns that actually exist in your table are written. It reflects your schema, so
    it works without knowing your model names. If a required column is missing it stops and
    prints the columns it found.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import MetaData, Table, create_engine, select, update

from app.ai.severity import (
    IMD_CODE_FAMILY, SEVERITY_RANK, ImdAlert, decide, extract_readings,
)

IMD_WINDOW_HOURS = 36  # an IMD "Day 1" warning only describes today's weather

IMD_CODE_NAME = {
    2: "Heavy Rain", 3: "Heavy Snow", 4: "Thunderstorm & Lightning", 5: "Hailstorm", 6: "Dust Storm",
    7: "Dust Raising Winds", 8: "Strong Surface Winds", 9: "Heat Wave", 10: "Hot Day", 11: "Warm Night",
    12: "Cold Wave", 13: "Cold Day", 14: "Ground Frost", 15: "Fog", 16: "Very Heavy Rain",
    17: "Extremely Heavy Rain",
}

COLUMN_CANDIDATES = {
    "id": ["id", "event_id"],
    "severity": ["severity"],
    "status": ["verification_status", "status"],
    "confidence": ["confidence_score", "credibility_score", "verification_score"],
    "city": ["city", "location_name", "location"],
    "state": ["state", "region"],
    "timestamp": ["timestamp", "event_timestamp", "created_at"],
    "description": ["description"],
    "risk_reasons": ["risk_reasons"],
}
REQUIRED = ["id", "severity", "status", "city", "state"]

# ---- name matching (mirrors frontend riskService.js) -----------------------
CITY_ALIASES = {
    "bangalore": "bengaluru", "bombay": "mumbai", "calcutta": "kolkata", "madras": "chennai",
    "gurgaon": "gurugram", "trivandrum": "thiruvananthapuram", "cochin": "kochi",
    "allahabad": "prayagraj", "poona": "pune", "baroda": "vadodara", "banaras": "varanasi",
    "benares": "varanasi", "mysore": "mysuru", "new delhi": "delhi", "khurda": "bhubaneswar",
}
STATE_ALIASES = {
    "orissa": "odisha", "uttaranchal": "uttarakhand", "nct of delhi": "delhi", "delhi nct": "delhi",
    "jammu and kashmir": "jammu kashmir", "pondicherry": "puducherry",
}
_DROP = re.compile(r"\b(district|dist|city|urban|rural|metropolitan|municipal corporation)\b")


def _clean(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or "").lower())
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).replace("&", " and ")
    s = _DROP.sub(" ", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def norm_city(s) -> str:
    c = _clean(s)
    return CITY_ALIASES.get(c, c)


def norm_state(s) -> str:
    c = _clean(s)
    return STATE_ALIASES.get(c, c)


def district_matches_city(district_norm: str, city_norm: str) -> bool:
    if not district_norm or not city_norm:
        return False
    if district_norm == city_norm:
        return True
    return city_norm in district_norm.split(" ") or district_norm.startswith(city_norm + " ")


# ---- IMD feed --------------------------------------------------------------
def fetch_imd(api_base: str) -> list[dict]:
    url = f"{api_base.rstrip('/')}/imd-warnings/?limit=756"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            payload = json.load(r)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        print(f"  ! Could not read IMD warnings from {url}: {exc}")
        print("    Continuing WITHOUT IMD corroboration (nothing can become 'verified').")
        return []
    return payload.get("warnings", []) if isinstance(payload, dict) else []


def build_imd_index(warnings: list[dict]) -> dict[str, list[ImdAlert]]:
    index: dict[str, list[ImdAlert]] = {}
    color_hist: Counter = Counter()
    for w in warnings:
        days = w.get("days") or []
        day1 = next((d for d in days if re.sub(r"\D", "", str(d.get("day", ""))) == "1"), days[0] if days else None)
        if not day1:
            continue
        try:
            color = int(day1.get("color_code"))
        except (TypeError, ValueError):
            continue
        color_hist[color] += 1
        codes = [int(c) for c in re.findall(r"\d+", str(day1.get("warning_code", ""))) if int(c) != 1]
        if color < 2 or not codes:
            continue
        index.setdefault(norm_state(w.get("state")), []).append(
            ImdAlert(
                district=w.get("district", "?"), color_code=color,
                families={IMD_CODE_FAMILY[c] for c in codes if c in IMD_CODE_FAMILY},
                types=[IMD_CODE_NAME.get(c, f"code {c}") for c in codes],
            )
        )
    if color_hist:
        print(f"  IMD Day-1 colour codes seen: {dict(sorted(color_hist.items()))}")
        print("  (sanity check: code 1 should be by far the most common - that is 'green / no warning')")
    return index


def find_alert(index: dict[str, list[ImdAlert]], city, state) -> ImdAlert | None:
    best = None
    cn = norm_city(city)
    for a in index.get(norm_state(state), []):
        if district_matches_city(norm_city(a.district), cn) and (best is None or a.color_code > best.color_code):
            best = a
    return best


# ---- helpers ---------------------------------------------------------------
def load_db_url(cli_value: str | None) -> str | None:
    if cli_value:
        return cli_value
    if os.getenv("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    for p in (Path(".env"), Path("..") / ".env", Path(__file__).resolve().parents[2] / ".env"):
        if p.exists():
            for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                m = re.match(r"\s*DATABASE_URL\s*=\s*(.+?)\s*$", line)
                if m:
                    return m.group(1).strip("'\"")
    return None


def to_utc(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return None


def pick(table: Table, names: list[str]) -> str | None:
    return next((n for n in names if n in table.c), None)


def norm_status(v) -> str:
    k = str(v or "").strip().lower().replace(" ", "_").replace("-", "_")
    if "unverif" in k or k in ("", "unknown", "none", "null"):
        return "unverified"
    if "review" in k:
        return "needs_review"
    if "pend" in k:
        return "pending"
    if "verif" in k:
        return "verified"
    if "reject" in k:
        return "rejected"
    return "unverified"


def norm_sev(v) -> str:
    k = str(v or "").strip().lower()
    if k in SEVERITY_RANK:
        return k
    if k in ("unknown", "", "none", "null"):
        return "unknown"
    return "low"


# ---- main ------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="write changes (default is a dry run)")
    ap.add_argument("--db-url")
    ap.add_argument("--api-base", default="http://127.0.0.1:8000")
    ap.add_argument("--events-table", default="events")
    ap.add_argument("--limit", type=int)
    args = ap.parse_args(argv)

    db_url = load_db_url(args.db_url)
    if not db_url:
        print("No database URL. Pass --db-url or set DATABASE_URL (env var or .env file).")
        return 2
    engine = create_engine(db_url)
    meta = MetaData()
    try:
        events = Table(args.events_table, meta, autoload_with=engine)
    except Exception as exc:  # noqa: BLE001
        print(f"Could not read table '{args.events_table}': {exc}")
        return 2

    cols = {k: pick(events, v) for k, v in COLUMN_CANDIDATES.items()}
    missing = [k for k in REQUIRED if not cols[k]]
    if missing:
        print(f"Table '{args.events_table}' is missing required columns for: {missing}")
        print(f"Columns found: {[c.name for c in events.columns]}")
        print("Tell me those column names (or edit COLUMN_CANDIDATES at the top of this file).")
        return 2
    print(f"Table '{args.events_table}' columns used: " + ", ".join(f"{k}={v}" for k, v in cols.items() if v))

    # optional sources table: event_id + raw_content (Open-Meteo payloads often live here)
    source_text: dict = {}
    for name in ("sources", "event_sources"):
        try:
            st = Table(name, meta, autoload_with=engine)
        except Exception:  # noqa: BLE001
            continue
        if "event_id" in st.c and "raw_content" in st.c:
            with engine.connect() as c:
                for ev_id, raw in c.execute(select(st.c.event_id, st.c.raw_content)):
                    if raw:
                        source_text.setdefault(ev_id, []).append(raw if isinstance(raw, (str, dict, list)) else str(raw))
            print(f"Loaded raw_content for {len(source_text)} events from '{name}'.")
            break

    print("Reading IMD warnings from the API ...")
    imd_index = build_imd_index(fetch_imd(args.api_base))
    imd_alert_districts = sum(len(v) for v in imd_index.values())
    print(f"  {imd_alert_districts} districts have a yellow/orange/red Day-1 warning.")

    now = datetime.now(timezone.utc)
    stmt = select(events)
    if args.limit and cols["timestamp"]:
        stmt = stmt.order_by(events.c[cols["timestamp"]].desc()).limit(args.limit)
    elif args.limit:
        stmt = stmt.limit(args.limit)

    before, after = Counter(), Counter()
    changes: list[tuple] = []
    with_readings = 0
    total = 0
    matched_imd_districts: set[str] = set()

    with engine.connect() as conn:
        rows = list(conn.execute(stmt).mappings())
    for row in rows:
        total += 1
        cur_status = norm_status(row[cols["status"]])
        cur_sev = norm_sev(row[cols["severity"]])
        before[(cur_sev, cur_status)] += 1
        if cur_status in ("verified", "rejected"):
            after[(cur_sev, cur_status)] += 1
            continue

        blobs = [row[cols["description"]] if cols["description"] else None]
        blobs += [v for k, v in row.items() if isinstance(v, (dict, list))]
        blobs += source_text.get(row[cols["id"]], [])
        readings = extract_readings(*blobs)
        if readings:
            with_readings += 1

        ts = to_utc(row[cols["timestamp"]]) if cols["timestamp"] else None
        fresh = ts is None or (now - ts) <= timedelta(hours=IMD_WINDOW_HOURS)
        alert = find_alert(imd_index, row[cols["city"]], row[cols["state"]]) if fresh else None
        if alert:
            matched_imd_districts.add(f"{norm_state(row[cols['state']])}|{norm_city(alert.district)}")

        d = decide(readings, alert, existing_severity=cur_sev)
        new_status = d.status
        if cur_status in ("needs_review", "pending") and new_status == "unverified":
            new_status = cur_status

        values = {}
        if d.severity != cur_sev:
            values[cols["severity"]] = d.severity
        if new_status != cur_status:
            values[cols["status"]] = new_status
        if cols["confidence"] and d.confidence is not None and row[cols["confidence"]] != d.confidence:
            values[cols["confidence"]] = d.confidence
        if cols["risk_reasons"] and d.reasons:
            values[cols["risk_reasons"]] = d.reasons if "JSON" in type(events.c[cols["risk_reasons"]].type).__name__.upper() else "; ".join(d.reasons)

        after[(d.severity if d.severity != cur_sev else cur_sev, new_status)] += 1
        if values:
            changes.append((row[cols["id"]], row[cols["city"]], row[cols["state"]], cur_sev, cur_status, d.severity, new_status, d.reasons, values))

    # ---- report ------------------------------------------------------------
    def table(counter: Counter, title: str) -> None:
        print(f"\n{title}")
        for (sev, st), n in sorted(counter.items(), key=lambda kv: (-SEVERITY_RANK.get(kv[0][0], 0), kv[0][1])):
            print(f"  {sev:9} {st:13} {n:6}")

    print(f"\nRows examined: {total}   rows with readings found: {with_readings}")
    if total and with_readings == 0:
        print("  ! No Open-Meteo readings could be found in your rows, so only IMD-based decisions are possible.")
        print("    Paste one row of your events table (and its sources.raw_content) and the extractor can be taught the format.")
    table(before, "BEFORE (severity / status)")
    table(after, "AFTER (what --apply would produce)")
    print(f"\nRows that would change: {len(changes)}")
    for c in changes[:15]:
        print(f"  id={c[0]} {c[1]}, {c[2]}: {c[3]}/{c[4]} -> {c[5]}/{c[6]}  | {'; '.join(c[7])[:140]}")
    if len(changes) > 15:
        print(f"  ... and {len(changes) - 15} more")

    if not args.apply:
        print("\nDRY RUN - nothing was written. Re-run with --apply to save these changes.")
        return 0
    if not changes:
        print("\nNothing to write.")
        return 0

    with engine.begin() as conn:
        for c in changes:
            conn.execute(update(events).where(events.c[cols["id"]] == c[0]).values(**c[8]))
    print(f"\nWrote {len(changes)} updates. Refresh the dashboard.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
