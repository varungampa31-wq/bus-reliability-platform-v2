"""
Phase 3 — Speed layer performance benchmark.

Measures per-record processing latency (add() + snapshot()) of the real
SlidingWindow class (shared/windowing.py) once the window has reached
steady state at a given sustained ingestion rate.

Because SlidingWindow is time-based (last N seconds), a higher sustained
rate means more events sit in the window at once, and snapshot() does an
O(window size) pass to compute per-route aggregates — so latency should
grow with load. That's a genuine, teachable scalability property, not just
"how fast can Python append to a deque".

Virtual timestamps (not real sleep) are used to fill the window to steady
state quickly, then a batch of "next" events at the same rate is timed —
this keeps the benchmark fast to run while still exercising the real
window-size-dependent cost.
"""

import csv
import random
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.windowing import SlidingWindow

RESULTS_DIR = Path("benchmark/results")
STATUSES = ["Excellent", "Good", "Average", "Poor", "Critical"]

WINDOW_SECONDS = 60          # shorter window keeps the benchmark fast
INGESTION_RATES = [5, 20, 50, 100, 250]   # events/sec sustained
MEASURE_BATCH_SIZE = 500     # records timed once steady state is reached


def _synthetic_record(i):
    return {
        "trip_id": f"synthetic_{i}",
        "route_id": f"ROUTE_{i % 50}",
        "reliability_score": random.choice([50, 60, 70, 80, 90, 100]),
        "status": random.choice(STATUSES),
    }


def run_latency_vs_rate_benchmark():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    results = []

    for rate in INGESTION_RATES:
        window = SlidingWindow(window_seconds=WINDOW_SECONDS)

        # --- fill window to steady state using virtual timestamps ---
        t = datetime.now(timezone.utc) - timedelta(seconds=WINDOW_SECONDS * 2)
        step = timedelta(seconds=1.0 / rate)
        steady_state_events = rate * WINDOW_SECONDS

        for i in range(steady_state_events):
            window.add(_synthetic_record(i), timestamp=t)
            t += step

        # --- measure latency of the next MEASURE_BATCH_SIZE events at this rate ---
        latencies = []
        start_wall = time.perf_counter()

        for i in range(MEASURE_BATCH_SIZE):
            record = _synthetic_record(steady_state_events + i)

            t0 = time.perf_counter()
            window.add(record, timestamp=t)
            window.snapshot(now=t)
            t1 = time.perf_counter()

            latencies.append((t1 - t0) * 1000)  # ms
            t += step

        elapsed_wall = time.perf_counter() - start_wall
        steady_state_window_size = window.snapshot(now=t)["total_events_in_window"]

        latencies.sort()
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[int(len(latencies) * 0.95)]
        p99 = latencies[int(len(latencies) * 0.99)]

        result = {
            "sustained_ingestion_rate_per_sec": rate,
            "window_seconds": WINDOW_SECONDS,
            "steady_state_window_size_events": steady_state_window_size,
            "records_measured": MEASURE_BATCH_SIZE,
            "processing_wall_time_seconds": round(elapsed_wall, 4),
            "p50_latency_ms": round(p50, 4),
            "p95_latency_ms": round(p95, 4),
            "p99_latency_ms": round(p99, 4),
        }
        results.append(result)
        print(result)

    out_csv = RESULTS_DIR / "speed_layer_latency.csv"
    with open(out_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    print(f"Speed layer latency results written to {out_csv}")
    return results


if __name__ == "__main__":
    print("=" * 60)
    print("SPEED LAYER BENCHMARK: latency vs. simulated ingestion rate")
    print("=" * 60)
    run_latency_vs_rate_benchmark()
