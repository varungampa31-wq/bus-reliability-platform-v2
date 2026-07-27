import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from producer.reliability import calculate_reliability


def _trip(stop_updates):
    return {"trip_id": "t1", "route_id": "R1", "number_of_stop_updates": stop_updates}


def test_score_bands():
    cases = [
        (0, 50, "Critical"),
        (1, 60, "Poor"),
        (3, 70, "Average"),
        (5, 80, "Good"),
        (7, 90, "Excellent"),
        (10, 100, "Excellent"),
        (25, 100, "Excellent"),
    ]
    for stop_updates, expected_score, expected_status in cases:
        result = calculate_reliability([_trip(stop_updates)])[0]
        assert result["reliability_score"] == expected_score, stop_updates
        assert result["status"] == expected_status, stop_updates


def test_preserves_original_fields():
    result = calculate_reliability([_trip(5)])[0]
    assert result["trip_id"] == "t1"
    assert result["route_id"] == "R1"


def test_empty_input():
    assert calculate_reliability([]) == []
