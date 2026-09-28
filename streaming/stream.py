from queue import Queue  # thread safe queue


# Shared in-memory queue that simulates our event stream.
event_stream = Queue()