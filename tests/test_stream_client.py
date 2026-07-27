import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.stream_client import LocalStreamClient


def test_put_and_read_new_records():
    with tempfile.TemporaryDirectory() as tmp:
        stream_path = Path(tmp) / "stream.jsonl"
        client = LocalStreamClient(path=stream_path)

        client.put_record({"trip_id": "1"})
        client.put_record({"trip_id": "2"})

        records = client.read_new_records()
        assert len(records) == 2
        assert records[0]["trip_id"] == "1"


def test_read_new_records_only_returns_unread_since_last_call():
    with tempfile.TemporaryDirectory() as tmp:
        stream_path = Path(tmp) / "stream.jsonl"
        client = LocalStreamClient(path=stream_path)

        client.put_record({"trip_id": "1"})
        first_batch = client.read_new_records()
        assert len(first_batch) == 1

        # nothing new yet
        assert client.read_new_records() == []

        client.put_record({"trip_id": "2"})
        second_batch = client.read_new_records()
        assert len(second_batch) == 1
        assert second_batch[0]["trip_id"] == "2"


def test_independent_consumers_have_independent_offsets():
    with tempfile.TemporaryDirectory() as tmp:
        stream_path = Path(tmp) / "stream.jsonl"
        producer = LocalStreamClient(path=stream_path)
        producer.put_record({"trip_id": "1"})

        consumer_a = LocalStreamClient(
            path=stream_path, consumer_state_path=Path(tmp) / "a.offset"
        )
        consumer_b = LocalStreamClient(
            path=stream_path, consumer_state_path=Path(tmp) / "b.offset"
        )

        assert len(consumer_a.read_new_records()) == 1
        # consumer_b hasn't read yet, so it should still see the record
        assert len(consumer_b.read_new_records()) == 1
        # both are now caught up
        assert consumer_a.read_new_records() == []
        assert consumer_b.read_new_records() == []


def test_record_count():
    with tempfile.TemporaryDirectory() as tmp:
        stream_path = Path(tmp) / "stream.jsonl"
        client = LocalStreamClient(path=stream_path)
        assert client.record_count() == 0
        client.put_record({"a": 1})
        client.put_record({"a": 2})
        assert client.record_count() == 2
