"""Fetch, assess and persist current Open-Meteo weather across India (one run).

Kept for backwards compatibility; equivalent to
    python -m backend.app.ingestion.run_live --source openmeteo
"""

from backend.app.ingestion.run_live import main

if __name__ == "__main__":
    main(["--source", "openmeteo"])
