"""
Sliding-window aggregation for the speed layer.

This is the core piece the original submission was missing: instead of a
cumulative running average since the consumer started, SlidingWindow only
retains events from the last `window_seconds` and evicts anything older on
every insert, so every snapshot() reflects "the last N minutes" rather than
"all time". The same class is used by:

  - speed_layer/local_speed_consumer.py  (LOCAL_MODE, polls the pseudo-stream)
  - speed_layer/lambda_function.py       (real AWS Lambda + DynamoDB TTL,
                                           conceptually the same window logic
                                           applied over items read back from
                                           DynamoDB instead of an in-memory deque)

Having one tested module backing both means the windowing logic itself is
unit-tested once (tests/test_windowing.py) rather than duplicated and
drifting between the local and Lambda versions.
"""

from collections import deque
from datetime import datetime, timedelta, timezone


def _now():
    return datetime.now(timezone.utc)


class SlidingWindow:
    def __init__(self, window_seconds=300):
        self.window_seconds = window_seconds
        self.events = deque()  # each item: (timestamp, record_dict)

    def add(self, record, timestamp=None):
        ts = timestamp or _now()
        self.events.append((ts, record))
        self._evict(ts)

    def _evict(self, now):
        cutoff = now - timedelta(seconds=self.window_seconds)
        while self.events and self.events[0][0] < cutoff:
            self.events.popleft()

    def snapshot(self, now=None, top_n=5):
        """Return the windowed aggregate as of `now` (defaults to current time).

        Passing `now` explicitly evicts stale events even if add() hasn't
        been called recently, so a snapshot taken during a quiet period
        still reflects an empty/shrinking window rather than stale data.
        """
        now = now or _now()
        self._evict(now)

        items = [r for _, r in self.events]
        total = len(items)

        scores = [
            float(r["reliability_score"])
            for r in items
            if "reliability_score" in r
        ]
        avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0

        status_counts = {"Excellent": 0, "Good": 0, "Average": 0, "Poor": 0, "Critical": 0}
        for r in items:
            status = r.get("status")
            if status in status_counts:
                status_counts[status] += 1

        per_route = {}
        for r in items:
            route = r.get("route_id", "UNKNOWN")
            per_route.setdefault(route, []).append(float(r.get("reliability_score", 0)))

        route_stats = [
            {
                "route_id": route,
                "avg_score": round(sum(vals) / len(vals), 2),
                "event_count": len(vals),
            }
            for route, vals in per_route.items()
        ]

        worst_routes = sorted(route_stats, key=lambda x: x["avg_score"])[:top_n]
        busiest_routes = sorted(route_stats, key=lambda x: -x["event_count"])[:top_n]

        return {
            "window_seconds": self.window_seconds,
            "generated_at": now.isoformat(),
            "total_events_in_window": total,
            "average_reliability_score": avg_score,
            "status_counts": status_counts,
            "top_worst_routes_in_window": worst_routes,
            "top_busiest_routes_in_window": busiest_routes,
            "all_routes_in_window": route_stats,
        }