"""
Speed Layer — AWS Lambda handler (real serverless deployment).

Wired to the Kinesis stream via an event source mapping (see
infrastructure/lambda/deploy_lambda.py), so Lambda invokes this handler
automatically each time a small batch of new records lands on the shard.

Windowing approach:
  Each incoming record is written to a DynamoDB table with a `ts` (unix
  epoch seconds) attribute and a `ttl` attribute set to now + window_seconds
  + a small grace period. DynamoDB's native TTL expiry keeps the table from
  growing unboundedly, and on every invocation we additionally query
  (Query against a GSI on a constant partition key, ordered/filtered by ts)
  only the items with ts >= now - window_seconds to compute the aggregate.
  That query result is the sliding window: it only ever reflects the last
  `WINDOW_SECONDS`, exactly like the local SlidingWindow class, just backed
  by DynamoDB instead of an in-memory deque so it survives across the many
  short-lived Lambda invocations.

  See infrastructure/lambda/dynamodb_table.json for the table + GSI
  definition this depends on (partition key `shard` = constant "ALL",
  sort key `ts`).
"""

import base64
import decimal
import json
import os
import time
from datetime import datetime, timezone

import boto3

DDB_TABLE = os.getenv("DDB_EVENTS_TABLE", "bus-speed-events")
WINDOW_SECONDS = int(os.getenv("WINDOW_SECONDS", "300"))
SUMMARY_S3_BUCKET = os.getenv("SUMMARY_S3_BUCKET")
SUMMARY_S3_KEY = os.getenv("SUMMARY_S3_KEY", "speed-layer/speed_output.json")
GSI_NAME = os.getenv("DDB_GSI_NAME", "shard-ts-index")
SHARD_KEY = "ALL"  # constant partition key for the GSI; fine at this data volume

dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")


def handler(event, context):
    table = dynamodb.Table(DDB_TABLE)
    now = int(time.time())
    written = 0

    for rec in event.get("Records", []):
        payload = base64.b64decode(rec["kinesis"]["data"])
        trip = json.loads(payload)

        table.put_item(
            Item={
                "event_id": rec["eventID"],
                "shard": SHARD_KEY,
                "route_id": trip.get("route_id", "UNKNOWN"),
                "status": trip.get("status", "Unknown"),
                "reliability_score": decimal.Decimal(str(trip.get("reliability_score", 0))),
                "ts": now,
                "ttl": now + WINDOW_SECONDS + 3600,
            }
        )
        written += 1

    summary = _compute_window_summary(table, now)

    if SUMMARY_S3_BUCKET:
        s3.put_object(
            Bucket=SUMMARY_S3_BUCKET,
            Key=SUMMARY_S3_KEY,
            Body=json.dumps(summary, indent=2).encode("utf-8"),
            ContentType="application/json",
        )

    return {"records_processed": written, "window_summary": summary}


def _compute_window_summary(table, now):
    cutoff = now - WINDOW_SECONDS

    response = table.query(
        IndexName=GSI_NAME,
        KeyConditionExpression="shard = :s AND ts >= :cutoff",
        ExpressionAttributeValues={":s": SHARD_KEY, ":cutoff": cutoff},
    )
    items = response.get("Items", [])

    total = len(items)
    scores = [float(i["reliability_score"]) for i in items if "reliability_score" in i]
    avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0

    status_counts = {"Excellent": 0, "Good": 0, "Average": 0, "Poor": 0, "Critical": 0}
    for i in items:
        status = i.get("status")
        if status in status_counts:
            status_counts[status] += 1

    per_route = {}
    for i in items:
        route = i.get("route_id", "UNKNOWN")
        per_route.setdefault(route, []).append(float(i.get("reliability_score", 0)))

    route_stats = [
        {"route_id": r, "avg_score": round(sum(v) / len(v), 2), "event_count": len(v)}
        for r, v in per_route.items()
    ]

    worst_routes = sorted(route_stats, key=lambda x: x["avg_score"])[:5]
    busiest_routes = sorted(route_stats, key=lambda x: -x["event_count"])[:5]

    return {
        "window_seconds": WINDOW_SECONDS,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_events_in_window": total,
        "average_reliability_score": avg_score,
        "status_counts": status_counts,
        "top_worst_routes_in_window": worst_routes,
        "top_busiest_routes_in_window": busiest_routes,
    }
