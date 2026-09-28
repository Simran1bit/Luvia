import json

from backend.app.services.event_persistence import save_event
from streaming.stream import event_stream


def consume_events():
    """Consume JSON messages and persist valid events to PostgreSQL."""

    consumed = 0
    saved = 0
    failed = 0

    while not event_stream.empty():
        message = event_stream.get()
        consumed += 1

        try:
            # Convert the JSON message back into a Python event dictionary.
            event = json.loads(message)

            # Persist the event and its related source/location records.
            event_id = save_event(event)
            saved += 1

            # Show only the first few successful records for a readable log.
            if saved <= 3:
                print(f"Saved event to database: event_id={event_id}")

        except Exception as error:
            # Keep processing other messages if one database operation fails.
            failed += 1
            print(f"Failed to save event {consumed}: {error}")

        finally:
            # Tell the queue that this message has been processed.
            event_stream.task_done()

    print("\nConsumer Summary")
    print("----------------")
    print(f"Consumed: {consumed}")
    print(f"Saved:    {saved}")
    print(f"Failed:   {failed}")

    return {
        "consumed": consumed,
        "saved": saved,
        "failed": failed,
    }