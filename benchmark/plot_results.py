"""
Generates the graphs required in Phase 3 ("plot relevant graphs: speedup vs
worker count, latency vs ingestion rate, throughput over time") from the CSV
output of benchmark_batch.py and benchmark_speed.py.

Run benchmark_batch.py and benchmark_speed.py first.
"""

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RESULTS_DIR = Path("benchmark/results")


def _read_csv(path):
    with open(path, "r", newline="") as f:
        return list(csv.DictReader(f))


def plot_speedup_vs_workers():
    path = RESULTS_DIR / "worker_scaling.csv"
    if not path.exists():
        print(f"Skipping (not found): {path}")
        return

    rows = _read_csv(path)
    workers = [int(r["workers"]) for r in rows]
    speedup = [float(r["speedup_vs_sequential"]) for r in rows]

    plt.figure(figsize=(6, 4))
    plt.plot(workers, speedup, marker="o", label="measured speedup")
    plt.plot(workers, workers, linestyle="--", color="gray", label="ideal (linear) speedup")
    plt.xlabel("Worker / core count (local[N])")
    plt.ylabel("Speedup vs. sequential (local[1])")
    plt.title("Batch Layer: Speedup vs. Worker Count")
    plt.legend()
    plt.tight_layout()
    out = RESULTS_DIR / "speedup_vs_workers.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"Saved {out}")


def plot_batch_time_vs_data_size():
    path = RESULTS_DIR / "data_size_scaling.csv"
    if not path.exists():
        print(f"Skipping (not found): {path}")
        return

    rows = _read_csv(path)
    sizes = [int(r["record_count"]) for r in rows]
    times = [float(r["elapsed_seconds"]) for r in rows]

    plt.figure(figsize=(6, 4))
    plt.plot(sizes, times, marker="o", color="tab:orange")
    plt.xlabel("Record count")
    plt.ylabel("Elapsed time (seconds)")
    plt.title("Batch Layer: Runtime vs. Data Volume")
    plt.tight_layout()
    out = RESULTS_DIR / "batch_time_vs_data_size.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"Saved {out}")


def plot_latency_vs_ingestion_rate():
    path = RESULTS_DIR / "speed_layer_latency.csv"
    if not path.exists():
        print(f"Skipping (not found): {path}")
        return

    rows = _read_csv(path)
    rates = [int(r["sustained_ingestion_rate_per_sec"]) for r in rows]
    p50 = [float(r["p50_latency_ms"]) for r in rows]
    p95 = [float(r["p95_latency_ms"]) for r in rows]
    p99 = [float(r["p99_latency_ms"]) for r in rows]

    plt.figure(figsize=(6, 4))
    plt.plot(rates, p50, marker="o", label="p50")
    plt.plot(rates, p95, marker="o", label="p95")
    plt.plot(rates, p99, marker="o", label="p99")
    plt.xlabel("Sustained ingestion rate (events/sec)")
    plt.ylabel("Per-record processing latency (ms)")
    plt.title("Speed Layer: Latency vs. Ingestion Rate")
    plt.legend()
    plt.tight_layout()
    out = RESULTS_DIR / "latency_vs_ingestion_rate.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"Saved {out}")


def plot_window_size_vs_rate():
    path = RESULTS_DIR / "speed_layer_latency.csv"
    if not path.exists():
        print(f"Skipping (not found): {path}")
        return

    rows = _read_csv(path)
    rates = [int(r["sustained_ingestion_rate_per_sec"]) for r in rows]
    window_sizes = [int(r["steady_state_window_size_events"]) for r in rows]

    plt.figure(figsize=(6, 4))
    plt.plot(rates, window_sizes, marker="o", color="tab:green")
    plt.xlabel("Sustained ingestion rate (events/sec)")
    plt.ylabel("Steady-state window size (events)")
    plt.title("Speed Layer: Window Size vs. Ingestion Rate")
    plt.tight_layout()
    out = RESULTS_DIR / "window_size_vs_rate.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"Saved {out}")


if __name__ == "__main__":
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    plot_speedup_vs_workers()
    plot_batch_time_vs_data_size()
    plot_latency_vs_ingestion_rate()
    plot_window_size_vs_rate()
