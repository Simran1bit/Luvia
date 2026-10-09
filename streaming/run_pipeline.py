import json

from backend.app.ingestion.pipeline import ingest_csv
from streaming.consumer import consume_events
from streaming.stream import event_stream


def run_pipeline(file_path: str):
    """Run the complete mock streaming pipeline."""

    produced = 0

    # Step 1: Generate valid events from the ingestion pipeline.
    for event in ingest_csv(file_path):

        # Step 2: Serialize each event before publishing.
        message = json.dumps(event)

        # Step 3: Publish the message to the mock stream.
        event_stream.put(message)

        produced += 1

    print(f"\nProducer published: {produced} events")

    # Step 4: Consumer reads everything currently in the stream.
    consume_events()


if __name__ == "__main__":
    run_pipeline("data/mock/weather_observations.csv")