from backend.app.ingestion.adapters.csv_adapter import read_csv
from backend.app.ingestion.normalizer import normalize_weather_event
from backend.app.ingestion.validator import validate_weather_event

def ingest_csv(file_path: str):
    """Read, normalize and validate CSV records one at a time."""

    total = 0
    valid = 0
    invalid = 0

    for row in read_csv(file_path):
        total += 1

        try:
            # Convert the raw source row into a LUVIA event.
            event = normalize_weather_event(row)

            # Check whether the normalized event is usable.
            is_valid, errors = validate_weather_event(event)

            if is_valid:
                valid += 1
                yield event

            else:
                invalid += 1
                print(f"Invalid row {total}: {errors}")

        except (KeyError, ValueError) as error:
            # Catch malformed rows without stopping the entire ingestion.
            invalid += 1
            print(f"Could not process row {total}: {error}")

    print("\nIngestion Summary")
    print("-----------------")
    print(f"Total rows:   {total}")
    print(f"Valid rows:   {valid}")
    print(f"Invalid rows: {invalid}")


if __name__ == "__main__":
    csv_path = "data/mock/weather_observations.csv"

    for index, event in enumerate(ingest_csv(csv_path)):

        # Show only the first 3 events for a readable terminal test.
        if index < 3:
            print("\nNormalized Event:")
            print(event)