from backend.app.services.event_persistence import save_event
from ingestion.pipeline import ingest_csv


if __name__ == "__main__":
    # Take the first valid event produced by the ingestion pipeline.
    event = next(
        ingest_csv("data/mock/weather_observations.csv")
    )

    print("Event being inserted:")
    print(event)

    # Persist the event and its related source/location records.
    event_id = save_event(event)

    print(f"\nSuccessfully inserted event_id: {event_id}")