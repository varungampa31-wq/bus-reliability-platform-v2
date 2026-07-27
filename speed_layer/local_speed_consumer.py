"""
Speed Layer — local/LOCAL_MODE consumer.

Polls the stream (real Kinesis or the local pseudo-stream, per STREAM_BACKEND)
for new records, feeds them into a SlidingWindow, and periodically writes a
windowed snapshot to data/speed-layer/speed_output.json.

This is the demo/dev-mode equivalent of speed_layer/lambda_function.py: the
same windowing logic (shared/windowing.py) is used by both, but this version
runs as a long-lived polling loop instead of being invoked per Kinesis batch
by AWS Lambda.
"""

import json
import os
import time
from pathlib import Path

from shared.stream_client import get_stream_client
from shared.windowing import SlidingWindow

WINDOW_SECONDS = int(os.getenv("SPEED_WINDOW_SECONDS", "300"))
POLL_INTERVAL_SECONDS = float(os.getenv("SPEED_POLL_INTERVAL_SECONDS", "1"))
OUTPUT_FILE = Path(
    os.getenv("SPEED_OUTPUT_FILE", "data/speed-layer/speed_output.json")
)


def run(max_iterations=None):
    """Run the polling loop. max_iterations is used by tests/benchmarks to
    stop after a bounded number of polls instead of running forever."""

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    client = get_stream_client()
    window = SlidingWindow(window_seconds=WINDOW_SECONDS)

    print("=" * 60)
    print(f"Speed Layer started (window={WINDOW_SECONDS}s, "
          f"poll_interval={POLL_INTERVAL_SECONDS}s)")
    print("=" * 60)

    iterations = 0
    total_processed = 0

    while max_iterations is None or iterations < max_iterations:
        new_records = client.read_new_records()

        for record in new_records:
            window.add(record)
            total_processed += 1

        snapshot = window.snapshot()
        snapshot["total_events_processed_all_time"] = total_processed

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2)

        if new_records:
            print(
                f"[+{len(new_records)}] window_total={snapshot['total_events_in_window']} "
                f"avg_score={snapshot['average_reliability_score']}"
            )

        iterations += 1
        time.sleep(POLL_INTERVAL_SECONDS)

    return snapshot


if __name__ == "__main__":
    run()
