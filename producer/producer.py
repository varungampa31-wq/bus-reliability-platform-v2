# Builds/loads the dataset, then replays it into the stream at a controlled rate.
# PRODUCER_LOOP_FOREVER=true keeps it running as a background service instead of a one-shot script.

import os
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

    loop_forever = os.getenv("PRODUCER_LOOP_FOREVER", "false").lower() == "true"
    cycle_sleep = float(os.getenv("PRODUCER_CYCLE_SLEEP_SECONDS", "30"))

    cycle = 0
    while True:
        cycle += 1
        if loop_forever:
            print(f"\n--- Cycle {cycle} ---")

        processed = build_processed_dataset()
        save_processed_dataset(processed)
        print_summary(processed)

        print("\nSending records to the ingestion stream...")
        replay_to_stream(processed)

        print("Producer cycle completed successfully.")

        if not loop_forever:
            break

        print(f"Sleeping {cycle_sleep}s before next cycle...")
        time.sleep(cycle_sleep)


if __name__ == "__main__":
    main()