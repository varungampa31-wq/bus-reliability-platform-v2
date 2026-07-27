"""
Builds the processed trip-updates dataset that gets replayed into the stream.

Tries the live GTFS-Realtime feed first (if GTFS_API_KEY is configured);
falls back to the stored seed dataset (data/raw/trip_updates.json) otherwise.
Either way, output is the same cleaned + scored schema, written to
data/processed/processed_trip_updates.json.
"""

import json
import os

from producer import config
from producer.gtfs_reader import download_feed
from producer.feed_parser import parse_feed, extract_trip_updates
from producer.data_cleaner import clean_trip_updates
from producer.reliability import calculate_reliability


def _load_seed_trips():
    seed_path = config.RAW_SEED_FILE
    if not os.path.exists(seed_path):
        raise FileNotFoundError(
            f"No live feed available and no seed file found at {seed_path}. "
            "Provide GTFS_API_KEY for a live feed or restore the seed file."
        )
    with open(seed_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_processed_dataset():
    """Returns the list of cleaned + scored trip records, live feed preferred."""

    feed_data = download_feed()

    if feed_data is not None:
        print("Using live GTFS-Realtime feed.")
        feed = parse_feed(feed_data)
        trips = extract_trip_updates(feed)
    else:
        print("Using stored seed dataset (data/raw/trip_updates.json).")
        trips = _load_seed_trips()

    cleaned = clean_trip_updates(trips)
    processed = calculate_reliability(cleaned)
    return processed


def save_processed_dataset(processed):
    os.makedirs(config.PROCESSED_FOLDER, exist_ok=True)
    output_path = os.path.join(config.PROCESSED_FOLDER, config.PROCESSED_FILE)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(processed, f, indent=2)

    print(f"Saved {len(processed)} processed records to {output_path}")
    return output_path


if __name__ == "__main__":
    data = build_processed_dataset()
    save_processed_dataset(data)
