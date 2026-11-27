DEFAULT_REQUIRED = ("temperature", "humidity", "rainfall")


def validate_weather_event(
    event: dict, required: tuple[str, ...] = DEFAULT_REQUIRED
) -> tuple[bool, list[str]]:
    """Validate required fields and basic weather value ranges.

    ``required`` lists the measurements that must be present. Sources that do
    not report every value (METAR has no rainfall amount) pass a shorter tuple;
    any value that *is* present is still range-checked.
    """

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

    for name, value in (
        ("temperature", temperature),
        ("humidity", humidity),
        ("rainfall", rainfall),
    ):
        if name in required and value is None:
            errors.append(f"{name} is missing")

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