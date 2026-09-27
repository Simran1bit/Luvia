# Simple CSV reader for streaming raw weather data into the ingestion pipeline.
import csv
from pathlib import Path


def read_csv(file_path: str):
    """
    Read a CSV file and yield one raw row at a time.
    """

    # Resolve the file path and fail early if the source data is missing.
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"CSV file not found: {file_path}"
        )

    with path.open("r", encoding="utf-8", newline="") as file:
        # Stream one row at a time to keep memory usage low for larger datasets.
        reader = csv.DictReader(file)
        yield from reader

"""
# Quick smoke test for the adapter during local development and debugging.
    
if __name__ == "__main__":
    csv_path = "data/mock/weather_observations.csv"

    for row in read_csv(csv_path):
        print(row)
        break
"""