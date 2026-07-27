# Architecture

## Problem & real-time question

**Which Dublin Bus routes' reliability has recently gotten worse than their historical average, and by how much?**

Each GTFS-Realtime trip update is scored into a Transit Reliability Index
(TRI, 0–100) based on how many stop-time updates the feed reports for that
trip (a proxy for how actively/accurately it's being tracked). The batch
layer answers "what is this route's reliability over all recorded history",
the speed layer answers "what is it in the last few minutes", and the
serving layer answers the actual question by combining both.

## Why Lambda architecture (not batch-only or stream-only)

- **Batch-only** would give accurate long-run reliability figures per route
  but couldn't tell you a route has just started running late *right now*
  — by the time a new batch run picks it up, the problem may already be over.
- **Stream-only** would give freshness but no defensible long-run baseline
  to compare against — "average score 65 today" means nothing without
  knowing that route's normal historical average.
- **Lambda architecture** gives both: the batch layer's full-history
  average is the baseline, the speed layer's sliding window is the current
  reading, and the serving layer's `recent_vs_history_delta` field is the
  actual actionable signal (see `serving/merge_view.py` /
  `athena/merged_view.sql`).

## Data flow

```
GTFS-Realtime feed (live, or stored seed replayed at a controlled rate)
        |
        v
   producer/producer.py  --clean & score-->  Kinesis Data Streams
        |                                           |
        v                                           v
EMR (PySpark, batch_processor_emr.py)      Lambda (lambda_function.py)
  full-history per-route + status            sliding-window (DynamoDB TTL)
  aggregates -> S3                            per-route recent stats -> S3
        |                                           |
        +-------------------+----------------------+
                             v
                    Athena merged_serving_view
                    (batch + speed, joined on route_id)
                             |
                             v
                   Flask dashboard (/api/merged)
```

All batch/speed compute runs on auto-scaling infrastructure:
EMR managed scaling (batch cluster) and an EC2 Auto Scaling Group
(producer/Flask), see `docs/aws_services.md` for triggers/cooldowns.

## What changed from the original submission

1. Fixed the broken `send_to_kinesis` import — ingestion now runs end-to-end.
2. Speed layer does real sliding-window aggregation (last N seconds), not a
   cumulative running average since consumer start.
3. Batch (EMR) job's `groupBy` fixed to match the actual data schema.
4. Batch + speed are combined into one serving view (Athena / `merge_view.py`)
   instead of two disconnected Flask endpoints.
5. Auto-scaling is a real, checked-in config (EMR managed scaling policy +
   EC2 ASG target-tracking policy) with stated triggers and cooldowns.
6. `benchmark/` is a real, runnable benchmark producing CSVs + graphs
   (speedup vs. worker count, runtime vs. data size, latency vs. ingestion
   rate) instead of an empty file.
7. `tests/` are real pytest unit tests with assertions (reliability scoring,
   data cleaning, feed parsing, windowing, stream client), not manual
   print-and-eyeball scripts.
