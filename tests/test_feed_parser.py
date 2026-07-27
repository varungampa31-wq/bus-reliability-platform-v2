import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.transit import gtfs_realtime_pb2
from producer.feed_parser import parse_feed, extract_trip_updates


def _build_sample_feed_bytes():
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"

    entity = feed.entity.add()
    entity.id = "1"
    entity.trip_update.trip.trip_id = "trip_1"
    entity.trip_update.trip.route_id = "1A"
    entity.trip_update.trip.start_date = "20260702"
    stop_update = entity.trip_update.stop_time_update.add()
    stop_update.stop_id = "stop_1"

    return feed.SerializeToString()


def test_parse_and_extract_round_trip():
    raw = _build_sample_feed_bytes()
    feed = parse_feed(raw)
    trips = extract_trip_updates(feed)

    assert len(trips) == 1
    assert trips[0]["trip_id"] == "trip_1"
    assert trips[0]["route_id"] == "1A"
    assert trips[0]["number_of_stop_updates"] == 1


def test_extract_ignores_entities_without_trip_update():
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    entity = feed.entity.add()
    entity.id = "1"
    entity.alert.cause = gtfs_realtime_pb2.Alert.OTHER_CAUSE

    trips = extract_trip_updates(feed)
    assert trips == []
