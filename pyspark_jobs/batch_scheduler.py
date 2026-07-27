# Runs the batch job on a repeating schedule, so it can be deployed as an always-on service.

import os
import time
import traceback

from pyspark_jobs.batch_processor_local import run_batch_job

BATCH_INTERVAL_SECONDS = float(os.getenv("BATCH_INTERVAL_SECONDS", "300"))
INPUT_PATH = os.getenv(
    "BATCH_INPUT_PATH", "data/processed/processed_trip_updates.json"
)
OUTPUT_PATH = os.getenv(
    "BATCH_OUTPUT_PATH", "data/batch-layer/batch_output.json"
)


def main():
    print("=" * 60)
    print(f"BATCH SCHEDULER — running every {BATCH_INTERVAL_SECONDS}s")
    print("=" * 60)

    while True:
        try:
            if os.path.exists(INPUT_PATH):
                result = run_batch_job(input_path=INPUT_PATH, output_path=OUTPUT_PATH)
                print(f"[batch cycle] {result}")
            else:
                print(f"[batch cycle] Skipped: {INPUT_PATH} does not exist yet.")
        except Exception:
            print("[batch cycle] ERROR:")
            traceback.print_exc()

        time.sleep(BATCH_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()