"""
One-shot speed layer processing: reads everything currently in the stream
file in a single pass and writes the windowed snapshot, then exits.
"""

import json
import os
from pathlib import Path

from shared.stream_client import get_stream_client
from shared.windowing import SlidingWindow

WINDOW_SECONDS = int(os.getenv("SPEED_WINDOW_SECONDS", "300"))
OUTPUT_FILE = Path(
    os.getenv("SPEED_OUTPUT_FILE", "data/speed-layer/speed_output.json")
)


def main():
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    client = get_stream_client()
    if hasattr(client, "reset_consumer"):
        client.reset_consumer()

    window = SlidingWindow(window_seconds=WINDOW_SECONDS)

    records = client.read_new_records()
    print(f"Read {len(records)} record(s) from the stream in one pass.")

    for record in records:
        window.add(record)

    snapshot = window.snapshot()
    snapshot["total_events_processed_all_time"] = len(records)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)

    print(f"Speed layer snapshot written to {OUTPUT_FILE}")
    print(f"  total_events_in_window: {snapshot['total_events_in_window']}")
    print(f"  average_reliability_score: {snapshot['average_reliability_score']}")


if __name__ == "__main__":
    main()
