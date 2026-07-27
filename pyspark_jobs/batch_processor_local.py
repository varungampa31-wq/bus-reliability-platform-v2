"""
Batch Layer — local/dev PySpark job.

Reads the accumulated processed dataset and computes the "correctness over
all history" batch view: per-route reliability statistics and an overall
status-distribution summary.

SPARK_MASTER controls parallelism (e.g. "local[1]", "local[4]", "local[*]"),
which is what benchmark/benchmark_batch.py varies to measure speedup vs.
worker/core count.
"""

import os
import sys
import time

from pyspark.sql import SparkSession
from pyspark.sql.functions import avg, count, stddev, min as spark_min, max as spark_max


def run_batch_job(input_path="data/processed/processed_trip_updates.json",
                   output_path="data/batch-layer/batch_output.json",
                   master=None):

    master = master or os.getenv("SPARK_MASTER", "local[*]")

    spark = (
        SparkSession.builder
        .appName("Bus Reliability Batch Processing")
        .master(master)
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")

    start = time.time()

    df = spark.read.option("multiline", "true").json(input_path)
    total_records = df.count()

    per_route = df.groupBy("route_id").agg(
        avg("reliability_score").alias("average_score"),
        count("*").alias("total_trips"),
        spark_min("reliability_score").alias("min_score"),
        spark_max("reliability_score").alias("max_score"),
    )

    status_distribution = df.groupBy("status").agg(count("*").alias("count"))

    per_route_pd = per_route.toPandas()
    status_pd = status_distribution.toPandas()

    elapsed = time.time() - start

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for _, row in per_route_pd.iterrows():
            f.write(row.to_json())
            f.write("\n")

    status_output_path = output_path.replace(".json", "_status_distribution.json")
    with open(status_output_path, "w", encoding="utf-8") as f:
        for _, row in status_pd.iterrows():
            f.write(row.to_json())
            f.write("\n")

    spark.stop()

    return {
        "master": master,
        "total_records": total_records,
        "elapsed_seconds": round(elapsed, 4),
        "routes_summarized": len(per_route_pd),
        "output_path": output_path,
    }


if __name__ == "__main__":
    input_path = sys.argv[1] if len(sys.argv) > 1 else "data/processed/processed_trip_updates.json"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "data/batch-layer/batch_output.json"

    print("=" * 60)
    print("DUBLIN BUS RELIABILITY BATCH PROCESSOR (local)")
    print("=" * 60)

    result = run_batch_job(input_path, output_path)
    print(result)
