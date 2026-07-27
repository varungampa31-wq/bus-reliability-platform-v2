"""
GTFS static lookup helper — resolves a route's source/destination stop names
from the static GTFS reference files (routes.txt, trips.txt, stop_times.txt,
stops.txt).
"""

import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GTFS_PATH = os.path.join(BASE_DIR, "data", "gtfs")

print("Loading GTFS static files...")

try:
    routes = pd.read_csv(os.path.join(GTFS_PATH, "routes.txt"))
    trips = pd.read_csv(os.path.join(GTFS_PATH, "trips.txt"))
    stop_times = pd.read_csv(os.path.join(GTFS_PATH, "stop_times.txt"))
    stops = pd.read_csv(os.path.join(GTFS_PATH, "stops.txt"))
    print("GTFS static files loaded successfully.")
except FileNotFoundError as e:
    print(f"GTFS static files not found: {e}")
    routes = trips = stop_times = stops = pd.DataFrame()


def get_route_source_destination(route_name, max_trips_to_try=50):
    """Resolves a route's source/destination stop names.

    Tries up to `max_trips_to_try` of the route's trips (not just the
    first) until it finds one with stop_times coverage. This matters
    because data/gtfs/stop_times.txt may be a trimmed sample of the full
    national feed — many individual trips have zero rows in the sample
    even though the route overall has coverage via other trips.
    """
    try:
        if routes.empty:
            return "Unknown", "Unknown"

        route_name = str(route_name).strip().upper()

        route = routes[
            routes["route_short_name"].astype(str).str.strip().str.upper() == route_name
        ]

        if route.empty:
            return "Unknown", "Unknown"

        route_id = route.iloc[0]["route_id"]
        route_trips = trips[trips["route_id"] == route_id]

        if route_trips.empty:
            return "Unknown", "Unknown"

        for _, trip_row in route_trips.head(max_trips_to_try).iterrows():
            trip_id = trip_row["trip_id"]
            trip_stops = stop_times[stop_times["trip_id"] == trip_id].sort_values("stop_sequence")

            if trip_stops.empty:
                continue

            first_stop = trip_stops.iloc[0]["stop_id"]
            last_stop = trip_stops.iloc[-1]["stop_id"]

            source = stops.loc[stops["stop_id"] == first_stop, "stop_name"].values
            destination = stops.loc[stops["stop_id"] == last_stop, "stop_name"].values

            if len(source) and len(destination):
                return source[0], destination[0]

        # none of the sampled trips had stop_times coverage
        return "Unknown", "Unknown"

    except Exception as e:
        print("GTFS ERROR:", e)
        return "Unknown", "Unknown"


def find_route_shorts_by_place(query):
    """Find route_short_name values for routes that serve a stop whose name
    contains `query` (case-insensitive substring match), e.g. "Ringsend" or
    "Adamstown". This is what makes place-name search work, as opposed to
    only matching against route_id strings like "1 E1 A".

    Note: stop_times.txt in this repo may be a trimmed sample of the full
    national GTFS feed (see README) — coverage for less-frequent routes may
    be incomplete unless the full file is used.
    """
    try:
        query = str(query).strip().upper()
        if not query or stops.empty:
            return set()

        matched_stops = stops[
            stops["stop_name"].astype(str).str.upper().str.contains(query, na=False)
        ]
        if matched_stops.empty:
            return set()

        stop_ids = set(matched_stops["stop_id"])

        matched_stop_times = stop_times[stop_times["stop_id"].isin(stop_ids)]
        if matched_stop_times.empty:
            return set()

        trip_ids = set(matched_stop_times["trip_id"])

        matched_trips = trips[trips["trip_id"].isin(trip_ids)]
        if matched_trips.empty:
            return set()

        route_ids = set(matched_trips["route_id"])

        matched_routes = routes[routes["route_id"].isin(route_ids)]
        return set(
            matched_routes["route_short_name"].astype(str).str.strip().str.upper()
        )

    except Exception as e:
        print("GTFS place search ERROR:", e)
        return set()


def extract_route_short(route_id):
    """Mirrors the convention used elsewhere in this project: a merged-view
    route_id like "2 245 C A" encodes the GTFS route_short_name as its
    second space-separated token ("245")."""
    try:
        parts = str(route_id).split()
        return parts[1].upper() if len(parts) > 1 else str(route_id).upper()
    except Exception:
        return str(route_id).upper()