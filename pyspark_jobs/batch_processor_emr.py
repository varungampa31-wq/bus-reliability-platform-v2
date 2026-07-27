"""
Batch Layer — EMR job (reads/writes S3).

Submitted as a spark-submit step on an EMR cluster (see
infrastructure/emr/launch_cluster.py). Reads the accumulated processed
dataset from S3 and writes the per-route batch view back to S3, where the
Athena serving layer reads it from (see athena/create_tables.sql).

Fix vs. the original submission: this now groups by "status" / aggregates
"reliability_score", matching the actual schema the producer writes
(trip_id, route_id, start_date, schedule_relationship,
number_of_stop_updates, reliability_score, status). The original grouped by
a "reliability" column that doesn't exist in the data, so it silently
produced a meaningless single/null group.
"""

import argparse

from pyspark.sql import SparkSession
from pyspark.sql.functions import avg, count, min as spark_min, max as spark_max


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="s3://bucket/raw-or-processed/ prefix")
    parser.add_argument("--output", required=True, help="s3://bucket/batch-output/ prefix")
    args = parser.parse_args()

    spark = (
        SparkSession.builder
        .appName("Bus Reliability Batch Processing - EMR")
        .getOrCreate()
    )

    print("=" * 60)
    print("EMR BATCH PROCESSOR")
    print("=" * 60)

    df = spark.read.json(args.input)

    print("Schema:")
    df.printSchema()

    total = df.count()
    print(f"Total records: {total}")

    per_route = df.groupBy("route_id").agg(
        avg("reliability_score").alias("average_score"),
        count("*").alias("total_trips"),
        spark_min("reliability_score").alias("min_score"),
        spark_max("reliability_score").alias("max_score"),
    )

    status_distribution = df.groupBy("status").agg(
        count("*").alias("total_trips"),
        avg("number_of_stop_updates").alias("avg_stop_updates"),
    )

    per_route.write.mode("overwrite").json(f"{args.output.rstrip('/')}/per_route/")
    status_distribution.write.mode("overwrite").json(f"{args.output.rstrip('/')}/status_distribution/")

    print("Batch processing completed successfully.")
    spark.stop()


if __name__ == "__main__":
    main()
