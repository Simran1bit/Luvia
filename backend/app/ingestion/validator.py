def validate_weather_event(event: dict) -> tuple[bool, list[str]]:
    """Validate required fields and basic weather value ranges."""

    errors = []

    location = event["location"]
    data = event["data"]

    latitude = location["latitude"]
    longitude = location["longitude"]

    temperature = data["temperature"]
    humidity = data["humidity"]
    rainfall = data["rainfall"]

    # Required numeric fields must be present.
    if latitude is None:
        errors.append("latitude is missing")

    if longitude is None:
        errors.append("longitude is missing")

    if temperature is None:
        errors.append("temperature is missing")

    if humidity is None:
        errors.append("humidity is missing")

    if rainfall is None:
        errors.append("rainfall is missing")

    # Geographic coordinates must stay within valid Earth ranges.
    if latitude is not None and not -90 <= latitude <= 90:
        errors.append("latitude is outside valid range")

    if longitude is not None and not -180 <= longitude <= 180:
        errors.append("longitude is outside valid range")

    # Humidity represents a percentage.
    if humidity is not None and not 0 <= humidity <= 100:
        errors.append("humidity is outside valid range")

    # Rainfall cannot physically be negative.
    if rainfall is not None and rainfall < 0:
        errors.append("rainfall cannot be negative")

    return len(errors) == 0, errors