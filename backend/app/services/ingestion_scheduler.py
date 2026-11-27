"""Background scheduler for all live ingestion jobs.

Started and stopped by the FastAPI lifespan in ``backend/app/main.py``.
IMD warnings run first at startup so weather observations ingested moments
later can be checked against fresh official alerts.

Set ``LUVIA_INGESTION_ENABLED=false`` to run the API without background jobs
(e.g. when running more than one Uvicorn worker, so only one process ingests).
"""

import logging
import os
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

from backend.app.ingestion.live_pipeline import INGESTORS

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="Asia/Kolkata")

# job name -> (interval in minutes, delay before first run in seconds)
JOBS = {
    "imd_warnings": (30, 0),
    # Open-Meteo then METAR in one job: Open-Meteo "current" updates every 15 min,
    # and METARs must attach to the Open-Meteo events, so they cannot run in parallel.
    "observations": (15, 45),
    "sachet": (10, 30),
    "imd_station": (30, 120),  # no-op until IMD_API_ENABLED=true
}


def _run(name: str) -> None:
    try:
        summary = INGESTORS[name]()
        failures = summary.pop("failures", [])
        logger.info("Ingestion %s complete: %s (failures=%d)", name, summary, len(failures))
        for failure in failures[:5]:
            logger.warning("Ingestion %s failure: %s", name, failure)
    except Exception:
        logger.exception("Ingestion job %s failed.", name)


def ingestion_enabled() -> bool:
    return os.getenv("LUVIA_INGESTION_ENABLED", "true").strip().lower() not in ("0", "false", "no")


def start_ingestion_scheduler() -> None:
    if not ingestion_enabled():
        logger.info("Live ingestion scheduler disabled by LUVIA_INGESTION_ENABLED.")
        return
    if scheduler.running:
        return

    now = datetime.now()
    for name, (minutes, delay) in JOBS.items():
        scheduler.add_job(
            _run,
            trigger="interval",
            args=[name],
            minutes=minutes,
            id=f"ingest_{name}",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            next_run_time=now + timedelta(seconds=delay),
        )

    scheduler.start()
    logger.info("Live ingestion scheduler started: %s", sorted(JOBS))


def stop_ingestion_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Live ingestion scheduler stopped.")
