"""Transparent keyword-based intent parsing; easy to extend."""
import re

LOCATIONS = ["Delhi", "Mumbai", "Chennai", "Kolkata", "Bengaluru", "Bangalore", "Hyderabad", "Pune", "Uttarakhand", "Rajasthan", "Maharashtra", "Kerala", "Assam", "India"]
CATEGORIES = ["flood", "floods", "rain", "rainfall", "heatwave", "heat waves", "cyclone", "storm", "drought", "landslide", "thunderstorm"]

def parse_intent(message: str, previous: dict | None = None):
    q = message.lower().strip()
    location = next((x for x in LOCATIONS if x.lower() in q), None) or (previous or {}).get("location")
    category = next((x for x in sorted(CATEGORIES, key=len, reverse=True) if x in q), None) or (previous or {}).get("category")
    if any(x in q for x in ("warning", "alert", "advisory")): intent = "warnings"
    elif any(x in q for x in ("forecast", "tomorrow", "next day", "next 3 days")): intent = "forecast"
    elif any(x in q for x in ("current weather", "weather in", "temperature", "raining", "rain right now", "is it raining")): intent = "weather"
    elif any(x in q for x in ("compare", "most events", "statistics", "trend", "how many")): intent = "analytics"
    elif any(x in q for x in ("event", "flood", "heatwave", "cyclone", "landslide", "drought", "severe weather", "occurred")): intent = "events"
    elif any(x in q for x in ("what is", "define", "how does luvia", "how are events", "precaution", "safety")): intent = "knowledge"
    elif any(x in q for x in ("tell me more", "more about", "that event", "this event")): intent = "event_detail"
    else: intent = "help"
    return {"intent": intent, "location": location, "category": category}
