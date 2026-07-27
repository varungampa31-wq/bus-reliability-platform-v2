import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.windowing import SlidingWindow


def test_snapshot_empty_window():
    w = SlidingWindow(window_seconds=60)
    snap = w.snapshot()
    assert snap["total_events_in_window"] == 0
    assert snap["average_reliability_score"] == 0.0


def test_events_within_window_are_counted():
    w = SlidingWindow(window_seconds=60)
    now = datetime.now(timezone.utc)
    w.add({"route_id": "1", "reliability_score": 80, "status": "Good"}, timestamp=now)
    w.add({"route_id": "1", "reliability_score": 100, "status": "Excellent"}, timestamp=now)
    snap = w.snapshot(now=now)
    assert snap["total_events_in_window"] == 2
    assert snap["average_reliability_score"] == 90.0
    assert snap["status_counts"]["Good"] == 1
    assert snap["status_counts"]["Excellent"] == 1


def test_old_events_are_evicted():
    w = SlidingWindow(window_seconds=60)
    old_ts = datetime.now(timezone.utc) - timedelta(seconds=120)
    w.add({"route_id": "1", "reliability_score": 50, "status": "Critical"}, timestamp=old_ts)

    now = datetime.now(timezone.utc)
    w.add({"route_id": "2", "reliability_score": 100, "status": "Excellent"}, timestamp=now)

    snap = w.snapshot(now=now)
    # only the recent event should remain; the 120s-old one is outside the 60s window
    assert snap["total_events_in_window"] == 1
    assert snap["average_reliability_score"] == 100.0


def test_snapshot_evicts_even_without_new_add():
    w = SlidingWindow(window_seconds=10)
    t0 = datetime.now(timezone.utc)
    w.add({"route_id": "1", "reliability_score": 60, "status": "Poor"}, timestamp=t0)

    later = t0 + timedelta(seconds=30)
    snap = w.snapshot(now=later)
    assert snap["total_events_in_window"] == 0


def test_worst_and_busiest_routes():
    w = SlidingWindow(window_seconds=60)
    now = datetime.now(timezone.utc)
    w.add({"route_id": "A", "reliability_score": 50, "status": "Critical"}, timestamp=now)
    w.add({"route_id": "A", "reliability_score": 50, "status": "Critical"}, timestamp=now)
    w.add({"route_id": "B", "reliability_score": 100, "status": "Excellent"}, timestamp=now)

    snap = w.snapshot(now=now, top_n=2)
    assert snap["top_worst_routes_in_window"][0]["route_id"] == "A"
    assert snap["top_busiest_routes_in_window"][0]["route_id"] == "A"
    assert snap["top_busiest_routes_in_window"][0]["event_count"] == 2
