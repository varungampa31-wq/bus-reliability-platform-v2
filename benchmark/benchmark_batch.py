"""
Phase 3 — Batch layer performance benchmark.

Runs the batch Spark job (pyspark_jobs/batch_processor_local.py) against the
same dataset repeatedly with different values of `local[N]`, timing each run,
and computes speedup relative to the N=1 (sequential) baseline. This is the
"compare sequential vs parallel execution of the batch job" requirement.

On a real machine/EMR cluster with more cores, edit WORKER_COUNTS below to
match available cores (e.g. [1, 2, 4, 8]). This sandbox has 1 CPU core, so
results here are for validating the script and CSV/plot pipeline, not for
claiming real speedup — rerun on adequate hardware for the report's numbers.

Also benchmarks scaling with dataset size (duplicating the base dataset N
times) at fixed parallelism, to show how batch runtime grows with data
volume — the other half of "measure throughput/latency/speedup under
different loads".
"""

import csv
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pyspark_jobs.batch_processor_local import run_batch_job

RESULTS_DIR = Path("benchmark/results")
BASE_INPUT = Path("data/processed/processed_trip_updates.json")

# Edit to match available cores on the machine actually running this.
WORKER_COUNTS = [int(x) for x in os.getenv("BENCHMARK_WORKER_COUNTS", "1,2,4").split(",")]
DATA_SIZE_MULTIPLIERS = [int(x) for x in os.getenv("BENCHMARK_DATA_MULTIPLIERS", "1,2,4").split(",")]


def _make_scaled_dataset(multiplier, out_path):
    with open(BASE_INPUT, "r", encoding="utf-8") as f:
        base = json.load(f)

    scaled = base * multiplier

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(scaled, f)

    return len(scaled)


def run_worker_scaling_benchmark():
    """Speedup vs. worker/core count, at fixed data size."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    baseline_time = None

    for n in WORKER_COUNTS:
        master = f"local[{n}]"
        result = run_batch_job(
            input_path=str(BASE_INPUT),
            output_path=f"benchmark/results/tmp_batch_output_{n}.json",
            master=master,
        )
        elapsed = result["elapsed_seconds"]

        if baseline_time is None:
            baseline_time = elapsed

        speedup = round(baseline_time / elapsed, 3) if elapsed > 0 else None

        results.append(
            {
                "workers": n,
                "elapsed_seconds": elapsed,
                "speedup_vs_sequential": speedup,
                "total_records": result["total_records"],
            }
        )
        print(results[-1])

    out_csv = RESULTS_DIR / "worker_scaling.csv"
    with open(out_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    print(f"Worker-scaling results written to {out_csv}")
    return results


def run_data_size_benchmark():
    """Elapsed time vs. dataset size, at fixed parallelism."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    fixed_master = f"local[{max(WORKER_COUNTS)}]"
    results = []

    for multiplier in DATA_SIZE_MULTIPLIERS:
        scaled_path = RESULTS_DIR / f"scaled_input_x{multiplier}.json"
        record_count = _make_scaled_dataset(multiplier, scaled_path)

        result = run_batch_job(
            input_path=str(scaled_path),
            output_path=f"benchmark/results/tmp_batch_output_x{multiplier}.json",
            master=fixed_master,
        )

        results.append(
            {
                "data_multiplier": multiplier,
                "record_count": record_count,
                "elapsed_seconds": result["elapsed_seconds"],
                "master": fixed_master,
            }
        )
        print(results[-1])

        scaled_path.unlink(missing_ok=True)

    out_csv = RESULTS_DIR / "data_size_scaling.csv"
    with open(out_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    print(f"Data-size scaling results written to {out_csv}")
    return results


if __name__ == "__main__":
    print("=" * 60)
    print("BATCH LAYER BENCHMARK: worker/core scaling")
    print("=" * 60)
    run_worker_scaling_benchmark()

    print("\n" + "=" * 60)
    print("BATCH LAYER BENCHMARK: data-size scaling")
    print("=" * 60)
    run_data_size_benchmark()
