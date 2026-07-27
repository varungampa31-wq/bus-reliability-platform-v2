"""
Configuration for the Bus Reliability Platform producer.

LOCAL_MODE=1 (default) uses the file-based pseudo-stream (shared/stream_client.py
LocalStreamClient) and, if no live GTFS API key is configured, falls back to the
stored seed dataset in data/raw/trip_updates.json. This lets the whole pipeline
run end-to-end without any AWS credentials or a live feed, per the "store +
paced replay = valid stream" rule.

Set STREAM_BACKEND=kinesis and provide AWS credentials + GTFS_API_KEY to run
against the real live feed and a real Kinesis stream.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# -------------------------------------------------------
# GTFS-Realtime live feed (optional — falls back to stored seed data)
# -------------------------------------------------------

GTFS_API_KEY = os.getenv("GTFS_API_KEY")
GTFS_FEED_URL = os.getenv(
    "GTFS_FEED_URL", "https://api.nationaltransport.ie/gtfsr/v2/gtfsr"
)

# -------------------------------------------------------
# Stream backend
# -------------------------------------------------------

STREAM_BACKEND = os.getenv("STREAM_BACKEND", "local")  # "local" | "kinesis"
KINESIS_STREAM_NAME = os.getenv("KINESIS_STREAM_NAME", "bus-trip-stream")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# -------------------------------------------------------
# Replay pacing
# -------------------------------------------------------

REPLAY_DELAY_SECONDS = float(os.getenv("REPLAY_DELAY_SECONDS", "1"))

# -------------------------------------------------------
# Local storage
# -------------------------------------------------------

RAW_SEED_FILE = os.getenv("RAW_SEED_FILE", "data/raw/trip_updates.json")
PROCESSED_FOLDER = os.getenv("PROCESSED_FOLDER", "data/processed")
PROCESSED_FILE = os.getenv("PROCESSED_FILE", "processed_trip_updates.json")

# -------------------------------------------------------
# S3 (used when publishing the processed dataset for the EMR batch job)
# -------------------------------------------------------

S3_BUCKET = os.getenv("S3_BUCKET")
S3_RAW_PREFIX = os.getenv("S3_RAW_PREFIX", "raw/")

PROJECT_NAME = "Bus Reliability Platform"
