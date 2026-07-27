"""
Serving-layer dashboard.

Unlike the original submission (two disconnected endpoints for batch vs.
speed), the primary endpoint here (/api/merged) serves the single merged
serving_layer view built by serving/merge_view.py — batch correctness and
speed freshness combined, per route. /api/batch and /api/speed are kept as
lower-level debug endpoints.
"""

import os
import sys
from pathlib import Path

from flask import Flask, jsonify, render_template

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask_api.gtfs_helper import (
    get_route_source_destination,
    find_route_shorts_by_place,
    extract_route_short,
)
from serving.merge_view import build_merged_view, _load_jsonl, _load_json, BATCH_FILE, SPEED_FILE

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/merged")
def merged():
    """The single combined serving view: batch history + speed-layer
    recent window, per route. Rebuilt on each call so the dashboard always
    reflects the latest speed-layer snapshot."""
    data = build_merged_view()
    return jsonify(data)


@app.route("/api/batch")
def batch():
    """Debug endpoint: raw batch-layer per-route output."""
    routes = _load_jsonl(BATCH_FILE)
    return jsonify({"total_routes": len(routes), "routes": routes})


@app.route("/api/speed")
def speed():
    """Debug endpoint: raw speed-layer windowed snapshot."""
    snapshot = _load_json(SPEED_FILE)
    return jsonify(snapshot or {"message": "No speed layer output yet."})


@app.route("/api/search/<query>")
def search_route(query):
    """Search matches on two independent things, unioned together:
      1. route_id substring match (e.g. "46A", "1 E1 A")
      2. place/stop name substring match (e.g. "Ringsend", "Adamstown"),
         resolved via the GTFS static stop_times/trips/routes join.
    Returns every matching route (not just the first), each enriched with
    its resolved source/destination stop names.
    """
    data = build_merged_view()
    query_lower = query.lower()

    id_matches = {r["route_id"] for r in data["routes"] if query_lower in r["route_id"].lower()}
    place_route_shorts = find_route_shorts_by_place(query)

    matches = []
    for r in data["routes"]:
        route_short = extract_route_short(r["route_id"])
        matched_by_id = r["route_id"] in id_matches
        matched_by_place = route_short in place_route_shorts

        if not (matched_by_id or matched_by_place):
            continue

        source, destination = get_route_source_destination(route_short)

        matches.append(
            {
                "route": route_short,
                "source": source,
                "destination": destination,
                "matched_by": "route_id" if matched_by_id else "place_name",
                **r,
            }
        )

    if not matches:
        return jsonify({"message": "No routes found", "query": query})

    return jsonify({"query": query, "total_matches": len(matches), "matches": matches})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
