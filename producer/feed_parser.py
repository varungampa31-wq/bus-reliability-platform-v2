"""
Parses GTFS-Realtime feed and extracts Trip Update information.
"""

from google.transit import gtfs_realtime_pb2


def parse_feed(feed_data):
    """Converts raw GTFS-Realtime protobuf data into a FeedMessage object."""
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(feed_data)
    return feed


def extract_trip_updates(feed):
    """Extract Trip Update information from the GTFS-Realtime feed."""
    trips = []

    for entity in feed.entity:
        if entity.HasField("trip_update"):
            trip_update = entity.trip_update
            trip = trip_update.trip

            trips.append(
                {
                    "trip_id": trip.trip_id,
                    "route_id": trip.route_id,
                    "start_date": trip.start_date,
                    "schedule_relationship": str(trip.schedule_relationship),
                    "number_of_stop_updates": len(trip_update.stop_time_update),
                }
            )

    return trips
