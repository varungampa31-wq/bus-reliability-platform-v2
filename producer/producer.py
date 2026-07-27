"""
Main Producer — Dublin Bus Reliability Intelligence Platform.

Builds (or loads) the processed dataset, then replays it into the ingestion
stream at a controlled rate (default: 1 record/second, configurable via
REPLAY_DELAY_SECONDS). This is the "paced replay" pattern the module
lecturers confirmed counts as a real stream: records arrive over time and
are processed incrementally by the speed layer, rather than being read as
one batch.

Fixes the bug in the original submission where producer.py imported a
`send_to_kinesis` function that was never defined — replay now goes through
the shared stream_client abstraction (shared/stream_client.py), which works
identically whether STREAM_BACKEND=local (no AWS needed) or
STREAM_BACKEND=kinesis (real Kinesis Data Streams).
"""

import time

from producer import config
from producer.build_dataset import build_processed_dataset, save_processed_dataset
from shared.stream_client import get_stream_client


def print_summary(data):
    print("\n================ SUMMARY ================")
    print(f"Total Records : {len(data)}")
    for status in ["Excellent", "Good", "Average", "Poor", "Critical"]:
        count = sum(1 for x in data if x["status"] == status)
        print(f"{status:<10}: {count}")
    print("=========================================\n")


def replay_to_stream(records, delay=None):
    """Replay processed records into the configured stream backend at a
    controlled rate."""

    delay = config.REPLAY_DELAY_SECONDS if delay is None else delay
    client = get_stream_client(backend=config.STREAM_BACKEND)

    print("=" * 60)
    print(f"Replaying {len(records)} records into stream "
          f"(backend={config.STREAM_BACKEND}, delay={delay}s)")
    print("=" * 60)

    for i, record in enumerate(records, start=1):
        client.put_record(record, partition_key=str(record.get("route_id", "default")))

        print(
            f"[{i}/{len(records)}] Route: {record.get('route_id')} | "
            f"Trip: {record.get('trip_id')} | "
            f"Score: {record.get('reliability_score')}"
        )

        time.sleep(delay)

    print("=" * 60)
    print("Replay completed.")
    print("=" * 60)


def main():
    print("=" * 70)
    print("DUBLIN BUS RELIABILITY INTELLIGENCE PLATFORM — PRODUCER")
    print("=" * 70)

    processed = build_processed_dataset()
    save_processed_dataset(processed)
    print_summary(processed)

    print("\nSending records to the ingestion stream...")
    replay_to_stream(processed)

    print("Producer completed successfully.")


if __name__ == "__main__":
    main()
