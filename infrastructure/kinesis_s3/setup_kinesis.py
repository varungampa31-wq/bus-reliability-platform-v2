"""
Creates the Kinesis Data Stream used for ingestion (idempotent).

Usage:
    python infrastructure/kinesis_s3/setup_kinesis.py

Requires AWS credentials configured (aws configure / env vars) with
kinesis:CreateStream / DescribeStream permissions.
"""

import os
import time

import boto3

STREAM_NAME = os.getenv("KINESIS_STREAM_NAME", "bus-trip-stream")
REGION = os.getenv("AWS_REGION", "us-east-1")
SHARD_COUNT = int(os.getenv("KINESIS_SHARD_COUNT", "1"))


def main():
    client = boto3.client("kinesis", region_name=REGION)

    try:
        client.describe_stream(StreamName=STREAM_NAME)
        print(f"Stream '{STREAM_NAME}' already exists.")
        return
    except client.exceptions.ResourceNotFoundException:
        pass

    print(f"Creating stream '{STREAM_NAME}' with {SHARD_COUNT} shard(s)...")
    client.create_stream(StreamName=STREAM_NAME, ShardCount=SHARD_COUNT)

    waiter = client.get_waiter("stream_exists")
    waiter.wait(StreamName=STREAM_NAME)
    print(f"Stream '{STREAM_NAME}' is ACTIVE.")


if __name__ == "__main__":
    main()
