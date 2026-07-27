"""
GTFS-Realtime Feed Reader.

Downloads the live GTFS-Realtime feed from the NTA API when a GTFS_API_KEY
is configured. Returns None on any failure so callers can fall back to the
stored seed dataset (see build_dataset.py) rather than crashing — this keeps
the pipeline runnable in environments without live network/API access.
"""

import requests

from producer.config import GTFS_API_KEY, GTFS_FEED_URL


def download_feed():
    """Downloads the GTFS-Realtime feed.

    Returns:
        bytes: raw protobuf data if successful.
        None: if the download fails or no API key is configured.
    """

    if not GTFS_API_KEY:
        print("No GTFS_API_KEY configured — skipping live feed download.")
        return None

    headers = {
        "Cache-Control": "no-cache",
        "x-api-key": GTFS_API_KEY,
    }

    try:
        print("Connecting to GTFS-Realtime API...")
        response = requests.get(GTFS_FEED_URL, headers=headers, timeout=30)
        response.raise_for_status()
        print("Feed downloaded successfully.")
        return response.content

    except requests.exceptions.RequestException as error:
        print(f"Download failed: {error}")
        return None
