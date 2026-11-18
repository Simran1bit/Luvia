
from backend.app.ingestion.adapters.imd_warning_adapter import (
    fetch_imd_district_warnings,
)
from backend.app.services.imd_warning_persistence import save_imd_warnings


def main():
    print("Fetching official IMD district warnings...")

    records = fetch_imd_district_warnings()
    print(f"Received {len(records)} district records from IMD.")

    result = save_imd_warnings(records)

    print("\nIMD ingestion completed.")
    print(f"Records saved or updated: {result['saved']}")
    print(f"Records skipped: {result['skipped']}")


if __name__ == "__main__":
    main()
