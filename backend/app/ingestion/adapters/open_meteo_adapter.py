
"""Fetch current weather snapshots for multiple Indian locations."""

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen


# Representative locations across India.
# Coordinates are approximate city-centre coordinates.
INDIAN_LOCATIONS = [
    {"location_name": "New Delhi", "state": "Delhi", "latitude": 28.6139, "longitude": 77.2090},
    {"location_name": "Mumbai", "state": "Maharashtra", "latitude": 19.0760, "longitude": 72.8777},
    {"location_name": "Kolkata", "state": "West Bengal", "latitude": 22.5726, "longitude": 88.3639},
    {"location_name": "Chennai", "state": "Tamil Nadu", "latitude": 13.0827, "longitude": 80.2707},
    {"location_name": "Bengaluru", "state": "Karnataka", "latitude": 12.9716, "longitude": 77.5946},
    {"location_name": "Hyderabad", "state": "Telangana", "latitude": 17.3850, "longitude": 78.4867},
    {"location_name": "Jaipur", "state": "Rajasthan", "latitude": 26.9124, "longitude": 75.7873},
    {"location_name": "Lucknow", "state": "Uttar Pradesh", "latitude": 26.8467, "longitude": 80.9462},
    {"location_name": "Bhopal", "state": "Madhya Pradesh", "latitude": 23.2599, "longitude": 77.4126},
    {"location_name": "Guwahati", "state": "Assam", "latitude": 26.1445, "longitude": 91.7362},
    {"location_name": "Srinagar", "state": "Jammu and Kashmir", "latitude": 34.0837, "longitude": 74.7973},
    {"location_name": "Bhubaneswar", "state": "Odisha", "latitude": 20.2961, "longitude": 85.8245},
    {"location_name": "Dehradun", "state": "Uttarakhand", "latitude": 30.3165, "longitude": 78.0322},
    {"location_name": "Patna", "state": "Bihar", "latitude": 25.5941, "longitude": 85.1376},
    {"location_name": "Thiruvananthapuram", "state": "Kerala", "latitude": 8.5241, "longitude": 76.9366},
]


def fetch_open_meteo(
    location_name="New Delhi",
    latitude=28.6139,
    longitude=77.2090,
    state=None,
):
    """Fetch one current weather snapshot in LUVIA's raw event format."""

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,precipitation",
        "timezone": "Asia/Kolkata",
    }

    url = "https://api.open-meteo.com/v1/forecast?" + urlencode(params)
    request = Request(
        url,
        headers={"User-Agent": "LUVIA-Weather-Intelligence/1.0"},
    )

    with urlopen(request, timeout=20) as response:
        result = json.loads(response.read().decode("utf-8"))

    current = result.get("current")
    if not current:
        raise ValueError(f"No current weather data returned for {location_name}.")

    return {
        "timestamp": current["time"],
        "location_name": location_name,
        "state": state,
        "latitude": latitude,
        "longitude": longitude,
        "temperature": current.get("temperature_2m"),
        "humidity": current.get("relative_humidity_2m"),
        "rainfall": current.get("precipitation"),
        "source": "OPEN_METEO",
    }


def fetch_india_weather():
    """Fetch snapshots across configured locations, continuing after individual failures."""

    results = []
    failures = []

    for location in INDIAN_LOCATIONS:
        try:
            results.append(fetch_open_meteo(**location))
            print(f"Fetched: {location['location_name']}, {location['state']}")
        except Exception as exc:
            failures.append({
                "location": location["location_name"],
                "error": str(exc),
            })
            print(f"Failed: {location['location_name']}: {exc}")

    return results, failures


if __name__ == "__main__":
    snapshots, failures = fetch_india_weather()
    print(f"\nSuccessful snapshots: {len(snapshots)}")
    print(f"Failed locations: {len(failures)}")
    print(json.dumps(snapshots, indent=2))
