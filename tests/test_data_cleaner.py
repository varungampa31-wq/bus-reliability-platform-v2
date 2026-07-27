import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from producer.data_cleaner import clean_trip_updates


def test_drops_records_missing_route_or_trip_id():
    trips = [
        {"trip_id": "", "route_id": "1A", "start_date": "20260101", "schedule_relationship": "0", "number_of_stop_updates": 1},
        {"trip_id": "t1", "route_id": "", "start_date": "20260101", "schedule_relationship": "0", "number_of_stop_updates": 1},
        {"trip_id": "t2", "route_id": "1a", "start_date": "20260101", "schedule_relationship": "0", "number_of_stop_updates": 1},
    ]
    cleaned = clean_trip_updates(trips)
    assert len(cleaned) == 1
    assert cleaned[0]["trip_id"] == "t2"


def test_uppercases_route_id():
    trips = [{"trip_id": "t1", "route_id": "2 64 d a", "start_date": "20260101", "schedule_relationship": "0", "number_of_stop_updates": 1}]
    cleaned = clean_trip_updates(trips)
    assert cleaned[0]["route_id"] == "2 64 D A"


def test_reformats_start_date():
    trips = [{"trip_id": "t1", "route_id": "1A", "start_date": "20260702", "schedule_relationship": "0", "number_of_stop_updates": 1}]
    cleaned = clean_trip_updates(trips)
    assert cleaned[0]["start_date"] == "2026-07-02"


def test_handles_unparseable_date_gracefully():
    trips = [{"trip_id": "t1", "route_id": "1A", "start_date": "not-a-date", "schedule_relationship": "0", "number_of_stop_updates": 1}]
    cleaned = clean_trip_updates(trips)
    assert cleaned[0]["start_date"] == "not-a-date"
