"""
Reliability Module.

Calculates a Transit Reliability Index (TRI) for each Trip Update, based on
how many stop-time updates GTFS-Realtime reported for that trip (a proxy for
how actively/accurately the trip is being tracked in real time).
"""


def calculate_reliability(trips):
    """Calculates a reliability score for each trip.

    Returns:
        list
    """

    results = []

    for trip in trips:
        stop_updates = trip["number_of_stop_updates"]

        if stop_updates >= 10:
            reliability = 100
        elif stop_updates >= 7:
            reliability = 90
        elif stop_updates >= 5:
            reliability = 80
        elif stop_updates >= 3:
            reliability = 70
        elif stop_updates >= 1:
            reliability = 60
        else:
            reliability = 50

        record = trip.copy()
        record["reliability_score"] = reliability

        if reliability >= 90:
            record["status"] = "Excellent"
        elif reliability >= 80:
            record["status"] = "Good"
        elif reliability >= 70:
            record["status"] = "Average"
        elif reliability >= 60:
            record["status"] = "Poor"
        else:
            record["status"] = "Critical"

        results.append(record)

    return results
