"""
Serving Layer — merges the batch view and speed view into a single view.

This is the actual "Lambda architecture merge" the brief asks for: the
original submission exposed batch and speed as two separate, unmerged Flask
endpoints. Here, for every route seen in the batch layer's full-history
aggregate, we attach the corresponding recent-window stats from the speed
layer (if any), plus an explicit "recent_vs_history_delta" so a viewer can
see at a glance whether a route's reliability is currently better or worse
than its historical average — exactly the kind of insight a Lambda
architecture is meant to produce (speed layer freshness + batch layer
correctness, combined).

On AWS, the equivalent merge is done in Athena via a view that joins the S3
batch-output table with the DynamoDB/S3 speed-output table
(see athena/merged_view.sql). This module is the local/offline equivalent,
used by the Flask app in LOCAL_MODE and for quick iteration.
"""

import json
import os
from pathlib import Path

BATCH_FILE = Path(os.getenv("BATCH_OUTPUT_FILE", "data/batch-layer/batch_output.json"))
SPEED_FILE = Path(os.getenv("SPEED_OUTPUT_FILE", "data/speed-layer/speed_output.json"))
MERGED_FILE = Path(os.getenv("MERGED_OUTPUT_FILE", "data/serving/merged_view.json"))


def _load_jsonl(path):
    if not path.exists():
        return []
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _load_json(path):
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_merged_view():
    batch_routes = _load_jsonl(BATCH_FILE)
    speed_snapshot = _load_json(SPEED_FILE) or {}

    speed_by_route = {
        r["route_id"]: r for r in speed_snapshot.get("all_routes_in_window", [])
    }

    merged_routes = []
    for route in batch_routes:
        route_id = route.get("route_id")
        recent = speed_by_route.get(route_id)

        entry = {
            "route_id": route_id,
            "historical_average_score": route.get("average_score"),
            "historical_total_trips": route.get("total_trips"),
            "recent_window_average_score": recent["avg_score"] if recent else None,
            "recent_window_event_count": recent["event_count"] if recent else 0,
        }

        if recent and route.get("average_score") is not None:
            entry["recent_vs_history_delta"] = round(
                recent["avg_score"] - route["average_score"], 2
            )
        else:
            entry["recent_vs_history_delta"] = None

        merged_routes.append(entry)

    merged = {
        "generated_at": speed_snapshot.get("generated_at"),
        "batch_layer": {
            "total_routes": len(batch_routes),
        },
        "speed_layer": {
            "window_seconds": speed_snapshot.get("window_seconds"),
            "total_events_in_window": speed_snapshot.get("total_events_in_window", 0),
            "average_reliability_score_recent": speed_snapshot.get("average_reliability_score"),
        },
        "routes": merged_routes,
    }

    MERGED_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MERGED_FILE, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2)

    return merged


if __name__ == "__main__":
    result = build_merged_view()
    print(f"Merged view written to {MERGED_FILE}")
    print(f"Routes: {len(result['routes'])}")