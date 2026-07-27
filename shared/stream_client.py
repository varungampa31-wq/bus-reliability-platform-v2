"""
Stream client abstraction.

Two backends implement the same interface (put_record / read_new_records):

  - LocalStreamClient   : file-based pseudo-stream (JSON Lines + offset file).
                          Used for LOCAL_MODE development/demo/testing without AWS.
                          Records are appended over time and consumed incrementally,
                          which satisfies the "paced replay = real stream" rule
                          (data arrives over time, processed incrementally, not a
                          one-shot file read).

  - KinesisStreamClient : real Amazon Kinesis Data Streams backend (boto3).

Select the backend with the STREAM_BACKEND env var ("local" or "kinesis"),
or pass backend= explicitly to get_stream_client().
"""

import json
import os
import time
from pathlib import Path


class LocalStreamClient:
    """File-based pseudo-stream for local development and automated testing.

    put_record() appends one JSON record per line to `path`.
    read_new_records() returns only records appended since the last call
    from *this* consumer (tracked via a sibling `.offset` file), which is
    what makes this behave like an incremental stream read rather than a
    batch file load.
    """

    def __init__(self, path, consumer_state_path=None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path = (
            Path(consumer_state_path)
            if consumer_state_path
            else self.path.with_suffix(".offset")
        )

    def put_record(self, record, partition_key=None):
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def read_new_records(self):
        offset = 0
        if self.state_path.exists():
            content = self.state_path.read_text().strip()
            offset = int(content) if content else 0

        if not self.path.exists():
            return []

        with open(self.path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        new_lines = lines[offset:]
        records = [json.loads(line) for line in new_lines if line.strip()]

        self.state_path.write_text(str(len(lines)))

        return records

    def reset_consumer(self):
        """Reset this consumer's read offset back to the start of the stream."""
        if self.state_path.exists():
            self.state_path.unlink()

    def record_count(self):
        if not self.path.exists():
            return 0
        with open(self.path, "r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())


class KinesisStreamClient:
    """Real Amazon Kinesis Data Streams backend."""

    def __init__(self, stream_name, region="us-east-1"):
        import boto3  # imported lazily so LOCAL_MODE never needs boto3/credentials

        self.client = boto3.client("kinesis", region_name=region)
        self.stream_name = stream_name
        self._shard_iterator = None

    def put_record(self, record, partition_key="default"):
        self.client.put_record(
            StreamName=self.stream_name,
            Data=json.dumps(record),
            PartitionKey=str(partition_key),
        )

    def _get_iterator(self):
        if self._shard_iterator:
            return self._shard_iterator

        desc = self.client.describe_stream(StreamName=self.stream_name)
        shard_id = desc["StreamDescription"]["Shards"][0]["ShardId"]

        self._shard_iterator = self.client.get_shard_iterator(
            StreamName=self.stream_name,
            ShardId=shard_id,
            ShardIteratorType="TRIM_HORIZON",
        )["ShardIterator"]

        return self._shard_iterator

    def read_new_records(self):
        iterator = self._get_iterator()
        response = self.client.get_records(ShardIterator=iterator, Limit=100)
        self._shard_iterator = response["NextShardIterator"]
        return [json.loads(r["Data"]) for r in response["Records"]]


def get_stream_client(backend=None):
    """Factory: returns a LocalStreamClient or KinesisStreamClient based on
    STREAM_BACKEND env var ("local" default, or "kinesis")."""

    backend = backend or os.getenv("STREAM_BACKEND", "local")

    if backend == "kinesis":
        return KinesisStreamClient(
            stream_name=os.getenv("KINESIS_STREAM_NAME", "bus-trip-stream"),
            region=os.getenv("AWS_REGION", "us-east-1"),
        )

    return LocalStreamClient(
        path=os.getenv("LOCAL_STREAM_PATH", "data/stream/local_stream.jsonl")
    )
