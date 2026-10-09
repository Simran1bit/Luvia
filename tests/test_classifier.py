
from ai.classifier import classify_event


def test_thunderstorm_is_classified_as_severe_weather():
    result = classify_event(
        "Thunderstorm in Delhi",
        "Lightning and strong winds reported."
    )

    assert result["category"] == "severe_weather"
    assert result["confidence"] == 0.90


def test_heavy_rain_keyword_is_detected():
    result = classify_event(
        "Heavy rain in Delhi",
        "A downpour has been reported."
    )

    assert result["category"] == "heavy_rainfall"
    assert result["confidence"] == 0.85


def test_rainfall_at_64_5_mm_is_heavy_rainfall():
    result = classify_event(
        "Weather observation",
        "Rainfall: 64.5 mm"
    )

    assert result["category"] == "heavy_rainfall"


def test_positive_rainfall_is_classified_as_rainfall():
    result = classify_event(
        "Weather observation",
        "Rainfall: 12.5 mm"
    )

    assert result["category"] == "rainfall"
    assert result["confidence"] == 0.80


def test_temperature_at_40_degrees_is_high_temperature():
    result = classify_event(
        "Weather observation",
        "Temperature: 40°C"
    )

    assert result["category"] == "high_temperature"
    assert result["confidence"] == 0.80


def test_normal_weather_observation_uses_default_category():
    result = classify_event(
        "Weather observation",
        "Temperature: 27.2°C, Humidity: 73.5%, Rainfall: 0.0 mm"
    )

    assert result["category"] == "weather_observation"
    assert result["confidence"] == 0.60
