from Chatbot.backend.intent import parse_intent

def test_weather_location():
    result = parse_intent("What's the current weather in Delhi?")
    assert result["intent"] == "weather"
    assert result["location"] == "Delhi"

def test_warning_intent():
    assert parse_intent("Any active warnings in Delhi?")["intent"] == "warnings"

def test_event_intent():
    result = parse_intent("Show recent floods in India")
    assert result["intent"] == "events"
    assert result["category"] == "floods"
