
"""Fetch historical hourly weather observations for configured Indian cities."""
import argparse
import json
from datetime import date, timedelta
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from backend.app.ingestion.adapters.open_meteo_adapter import INDIAN_LOCATIONS


def fetch_historical_weather(location, start_date, end_date):
    params = {
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "start_date": start_date,
        "end_date": end_date,
        "hourly": (
            "temperature_2m,relative_humidity_2m,"
            "precipitation,wind_speed_10m,weather_code"
        ),
        "timezone": "Asia/Kolkata",
    }

    url = (
        "https://archive-api.open-meteo.com/v1/archive?"
        + urlencode(params)
    )
    request = Request(
        url,
        headers={"User-Agent": "LUVIA-Weather-Intelligence/1.0"},
    )

    with urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))

    hourly = payload.get("hourly", {})
    times = hourly.get("time", [])

    records = []
    for i, timestamp in enumerate(times):
        records.append({
            "timestamp": timestamp,
            "location_name": location["location_name"],
            "state": location["state"],
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "temperature": hourly["temperature_2m"][i],
            "humidity": hourly["relative_humidity_2m"][i],
            "rainfall": hourly["precipitation"][i],
            "wind_speed": hourly["wind_speed_10m"][i],
            "weather_code": hourly["weather_code"][i],
            "source": "OPEN_METEO_ARCHIVE",
        })

    return records


def main():
    # A completed historical window avoids requesting incomplete current-day data.
    end_date = date.today() - timedelta(days=2)
    start_date = end_date - timedelta(days=13)

    print(f"Historical window: {start_date} to {end_date}")
    print("Fetching observations. No database records will be changed.")

    all_records = []
    failures = []

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--states",
        nargs="+",
        help="Only fetch locations belonging to these states",
    )
    args = parser.parse_args()

    locations = INDIAN_LOCATIONS

    if args.states:
        requested = {state.strip().casefold() for state in args.states}
        locations = [
            location for location in INDIAN_LOCATIONS
            if location["state"].strip().casefold() in requested
        ]

        missing = requested - {
            location["state"].strip().casefold()
            for location in locations
        }
        if missing:
            parser.error(f"No configured locations for: {sorted(missing)}")

    for location in locations:
        try:
            records = fetch_historical_weather(
                location,
                start_date.isoformat(),
                end_date.isoformat(),
            )
            all_records.extend(records)
            print(f"{location['location_name']}: {len(records)} observations")
        except Exception as exc:
            failures.append({
                "city": location["location_name"],
                "error": str(exc),
            })
            print(f"FAILED {location['location_name']}: {exc}")

    output_file = "data/processed/historical_weather_preview.json"
    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(all_records, file, indent=2)

    print("\n--- Historical Weather Preview ---")
    print(f"Total observations fetched: {len(all_records)}")
    print(f"Cities configured: {len(INDIAN_LOCATIONS)}")
    print(f"Cities failed: {len(failures)}")
    print(f"Preview saved to: {output_file}")

    if failures:
        print(json.dumps(failures, indent=2))


if __name__ == "__main__":
    main()
