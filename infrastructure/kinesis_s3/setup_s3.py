"""
Creates the S3 bucket used for raw archive + batch output + speed output
(idempotent).

Usage:
    S3_BUCKET=my-bus-reliability-bucket python infrastructure/kinesis_s3/setup_s3.py
"""

import os

import boto3

BUCKET_NAME = os.environ["S3_BUCKET"]  # required — no sane default for a globally-unique bucket name
REGION = os.getenv("AWS_REGION", "us-east-1")


def main():
    client = boto3.client("s3", region_name=REGION)

    existing = [b["Name"] for b in client.list_buckets().get("Buckets", [])]
    if BUCKET_NAME in existing:
        print(f"Bucket '{BUCKET_NAME}' already exists.")
        return

    print(f"Creating bucket '{BUCKET_NAME}' in {REGION}...")
    if REGION == "us-east-1":
        client.create_bucket(Bucket=BUCKET_NAME)
    else:
        client.create_bucket(
            Bucket=BUCKET_NAME,
            CreateBucketConfiguration={"LocationConstraint": REGION},
        )

    for prefix in ["raw/", "processed/", "batch-output/", "speed-layer/"]:
        client.put_object(Bucket=BUCKET_NAME, Key=prefix)

    print(f"Bucket '{BUCKET_NAME}' created with raw/, processed/, batch-output/, speed-layer/ prefixes.")


if __name__ == "__main__":
    main()
