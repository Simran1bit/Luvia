
from sqlalchemy import text

from backend.app.database import engine
from backend.app.ai.classifier import classify_event
from backend.app.ai.similarity import compare_reports

def save_prediction(event_id, prediction_type, prediction, confidence):
    query = text("""
        INSERT INTO model_predictions (
            event_id,
            model_name,
            prediction_type,
            prediction,
            confidence
        )
        VALUES (
            :event_id,
            :model_name,
            :prediction_type,
            :prediction,
            :confidence
        )
    """)

    with engine.begin() as connection:
        connection.execute(
            query,
            {
                "event_id": event_id,
                "model_name": "LUVIA-AI-v1",
                "prediction_type": prediction_type,
                "prediction": prediction,
                "confidence": confidence,
            },
        )

def analyze_events():
    # Fetch the 20 most recent events from PostgreSQL.
    query = text("""
        SELECT event_id, title, description, city, event_timestamp
        FROM events
        ORDER BY event_id DESC
        LIMIT 20
    """)

    with engine.connect() as connection:
        events = connection.execute(query).mappings().all()

    if not events:
        print("No events found in the database.")
        return

    print(f"Analyzing {len(events)} weather events...\n")

    for event in events:
        title = event["title"] or ""
        description = event["description"] or ""

        # Step 1: Classify the event.
        result = classify_event(title, description)

        save_prediction(
            event_id=event["event_id"],
            prediction_type="weather_classification",
            prediction=result["category"],
            confidence=result["confidence"],
        )

        print(f"Event ID: {event['event_id']}")
        print(f"Title: {title}")
        print(f"City: {event['city']}")
        print(f"Category: {result['category']}")
        print(f"Rule confidence: {result['confidence']}")

        # Step 2: Compare this event with another recent event.
        # Compare only events from the same city.
        
        current_text = f"{title} {description}"
        matches = []

        for other in events:
            if other["event_id"] == event["event_id"]:
                continue

            current_city = (event["city"] or "").strip().lower()
            other_city = (other["city"] or "").strip().lower()

            # Compare only reports with known, matching cities.
            if not current_city or current_city != other_city:
                continue

            other_text = (
                f"{other['title'] or ''} "
                f"{other['description'] or ''}"
            )

            score = compare_reports(current_text, other_text)

            if score >= 0.70:
                matches.append({
                    "event_id": other["event_id"],
                    "similarity": score
                })

        if matches:
            matches.sort(
                key=lambda match: match["similarity"],
                reverse=True
            )

            print("Potentially related reports:")

            for match in matches:
                print(
                    f"Event {match['event_id']} | "
                    f"Similarity: {match['similarity']}"
                )
        else:
            print("No strong text-similarity matches found.")

            save_prediction(
                event_id=event["event_id"],
                prediction_type="text_similarity",
                prediction=f"Compared with event {other['event_id']}: {score}",
                confidence=score,
            )

            print(
                f"Similarity with event {other['event_id']}: "
                f"{score:.4f}"
            )
            break

        print("-" * 40)


if __name__ == "__main__":
    analyze_events()
