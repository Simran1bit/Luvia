"""Run live ingestion once from the command line.

    python -m backend.app.ingestion.run_live                 # every source, IMD warnings first
    python -m backend.app.ingestion.run_live --source metar  # one source

Sources: imd_warnings, observations (= openmeteo then metar), openmeteo, metar,
sachet, imd_station.
The API server runs the same jobs on a schedule (services/ingestion_scheduler.py).
"""

import argparse
import json

from dotenv import load_dotenv

load_dotenv()

from backend.app.ingestion.live_pipeline import INGESTORS  # noqa: E402  (needs env first)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", choices=sorted(INGESTORS), action="append",
                        help="source to ingest (repeatable); default is all, in dependency order")
    parser.add_argument("--once", action="store_true", help="accepted for clarity; the CLI always runs once")
    args = parser.parse_args(argv)

    # IMD warnings first; "observations" already runs Open-Meteo then METAR.
    sources = args.source or ["imd_warnings", "observations", "sachet", "imd_station"]
    for name in sources:
        print(f"\n=== {name} ===")
        try:
            summary = INGESTORS[name]()
        except Exception as exc:
            print(f"FAILED: {exc}")
            continue

        failures = summary.pop("failures", [])
        print(json.dumps(summary, indent=2, default=str))
        if failures:
            print(f"{len(failures)} failure(s):")
            for failure in failures[:10]:
                print(f"  - {failure}")
            if len(failures) > 10:
                print(f"  ... and {len(failures) - 10} more")


if __name__ == "__main__":
    main()
