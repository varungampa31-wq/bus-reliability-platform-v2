"""
Data Cleaning Module.
Cleans Trip Update data before analytics.
"""

from datetime import datetime


def clean_trip_updates(trips):
    """Cleans Trip Update records.

    Returns:
        list
    """

    cleaned = []

    for trip in trips:
        route_id = str(trip.get("route_id", "")).strip()
        trip_id = str(trip.get("trip_id", "")).strip()
        start_date = trip.get("start_date", "")
        stop_updates = trip.get("number_of_stop_updates", 0)

        if route_id == "" or trip_id == "":
            continue

        try:
            formatted_date = datetime.strptime(str(start_date), "%Y%m%d").strftime(
                "%Y-%m-%d"
            )
        except ValueError:
            formatted_date = start_date

        cleaned.append(
            {
                "trip_id": trip_id,
                "route_id": route_id.upper(),
                "start_date": formatted_date,
                "schedule_relationship": str(trip.get("schedule_relationship", "0")),
                "number_of_stop_updates": stop_updates,
            }
        )

    return cleaned
