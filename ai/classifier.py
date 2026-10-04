
import re


def classify_event(title: str, description: str) -> dict:
    """
    Assign a weather category using simple rules.

    This is a baseline classifier, not a trained AI model.
    """

    # Combine the title and description for easier searching.
    text = f"{title} {description}".lower()

    # Check for explicit severe-weather keywords first.
    if any(word in text for word in [
        "thunderstorm", "lightning", "tornado"
    ]):
        category = "severe_weather"
        confidence = 0.90

    # Look for heavy-rain keywords.
    elif any(word in text for word in [
        "heavy rain", "downpour", "cloudburst"
    ]):
        category = "heavy_rainfall"
        confidence = 0.85

    # Extract a rainfall measurement, if present.
    else:
        rainfall_match = re.search(
            r"rainfall:\s*(-?\d+(?:\.\d+)?)\s*mm",
            text
        )

        # Extract temperature, if present.
        temperature_match = re.search(
            r"temperature:\s*(-?\d+(?:\.\d+)?)\s*°?c",
            text
        )

        rainfall = (
            float(rainfall_match.group(1))
            if rainfall_match else None
        )

        temperature = (
            float(temperature_match.group(1))
            if temperature_match else None
        )

        if rainfall is not None and rainfall >= 64.5:
            category = "heavy_rainfall"
            confidence = 0.85

        elif rainfall is not None and rainfall > 0:
            category = "rainfall"
            confidence = 0.80

        elif temperature is not None and temperature >= 40:
            category = "high_temperature"
            confidence = 0.80

        else:
            category = "weather_observation"
            confidence = 0.60

    return {
        "category": category,
        "confidence": confidence
    }
