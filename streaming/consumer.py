import json

from streaming.stream import event_stream


def consume_events():
    """Read JSON messages from the stream and convert them back to events."""

    consumed = 0

    while not event_stream.empty():
        message = event_stream.get()

        try:
            # Deserialize the JSON message back into a Python dictionary.
            event = json.loads(message)

            consumed += 1

            if consumed <= 3:
                print("\nConsumed Event:")
                print(event)

        finally:
            # Mark this message as successfully removed from the queue.
            event_stream.task_done()

    print(f"\nConsumer processed {consumed} events.")

