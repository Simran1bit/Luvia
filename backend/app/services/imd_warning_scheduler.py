
import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

from backend.app.ingestion.adapters.imd_warning_adapter import (
    fetch_imd_district_warnings,
)
from backend.app.services.imd_warning_persistence import save_imd_warnings

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="Asia/Kolkata")


def refresh_imd_data():
    """Fetch official IMD warnings and update Neon."""
    try:
        logger.info("Starting scheduled IMD warning refresh.")

        records = fetch_imd_district_warnings()
        result = save_imd_warnings(records)

        logger.info(
            "IMD refresh complete: received=%s saved=%s skipped=%s",
            len(records),
            result["saved"],
            result["skipped"],
        )
    except Exception:
        logger.exception("Scheduled IMD warning refresh failed.")



def start_imd_scheduler():
    print("[LUVIA] Starting IMD scheduler...")

    if scheduler.running:
        print("[LUVIA] Scheduler is already running.")
        return

    scheduler.add_job(
        refresh_imd_data,
        trigger="interval",
        minutes=30,
        id="imd_warning_refresh",
        replace_existing=True,
        max_instances=1,
        next_run_time=datetime.now(),
    )

    scheduler.start()

    print("[LUVIA] IMD scheduler started.")
    print(f"[LUVIA] Scheduled jobs: {scheduler.get_jobs()}")


def stop_imd_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("IMD scheduler stopped.")
