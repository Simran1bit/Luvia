from ai.classifier import classify_event


# Test the weather data format already stored in LUVIA.
result = classify_event(
    "Weather observation — Gurugram",
    "Temperature: 31.4°C, Humidity: 73.5%, Rainfall: 0.0 mm"
)

print(result)


# Test a report containing a heavy-rain keyword.
result = classify_event(
    "Heavy rain in Delhi",
    "A downpour has been reported."
)

print(result)
