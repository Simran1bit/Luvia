import json

from ingestion.pipeline import ingest_csv
from streaming.stream import event_stream


def produce_events(file_path: str):
    """Read valid LUVIA events and publish them to the stream."""

    produced = 0

    for event in ingest_csv(file_path):
        # Serialize the event so the stream carries JSON-like data.
        message = json.dumps(event)

        event_stream.put(message)
        produced += 1

    print(f"Producer published {produced} events.")


if __name__ == "__main__":
    produce_events("data/mock/weather_observations.csv")