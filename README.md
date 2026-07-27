# Dublin Bus Reliability Intelligence Platform

**Module:** Scalable Cloud Programming — National College of Ireland
**Architecture:** Lambda architecture (batch + speed + serving layers), auto-scaling on AWS.

Real-time analytics over Dublin Bus GTFS-Realtime trip updates: scores each
trip's reliability, computes a full-history batch view (EMR/Spark) and a
sliding-window speed view (Lambda), and merges both into one serving view
(Athena) shown on a live Flask dashboard.

See `docs/architecture.md` for the data-flow diagram and design rationale,
`docs/aws_services.md` for the full service list and auto-scaling
triggers/cooldowns, and `docs/deployment_guide.md` for setup instructions
(both local demo mode and real AWS deployment).

## Quick start (local demo, no AWS needed)

```bash
pip install -r requirements.txt
python -m producer.producer
python -m speed_layer.local_speed_consumer   # Ctrl+C after a few seconds
python pyspark_jobs/batch_processor_local.py
python -m serving.merge_view
python -m flask_api.app
```

Then open http://localhost:5000.

## Running the tests

```bash
python -m pytest tests/ -v
```

## Running the Phase 3 benchmarks

```bash
python benchmark/benchmark_batch.py
python benchmark/benchmark_speed.py
python benchmark/plot_results.py
```

## Repository layout

```
producer/           GTFS feed download/parse/clean/score + paced replay into the stream
shared/              Stream client abstraction (local pseudo-stream / real Kinesis) + sliding-window logic
speed_layer/         Windowed speed layer: local dev consumer + real AWS Lambda handler
pyspark_jobs/        Batch layer: local dev job + real EMR job
serving/             Merges batch + speed into one serving view (local); athena/ holds the AWS-side SQL equivalent
athena/              Athena table + merged-view SQL for the serving layer
flask_api/           Dashboard reading the merged serving view
benchmark/           Phase 3 performance benchmarks (speedup vs workers, latency vs ingestion rate) + plots
infrastructure/      boto3/IaC scripts: Kinesis, S3, EMR (+managed scaling), Lambda, DynamoDB, EC2 ASG
tests/               pytest unit tests for the core logic
docs/                Architecture, AWS services, deployment guide
data/                GTFS static reference files + seed dataset for local/demo replay
```

## Notes

- `data/gtfs/stop_times.txt` is a 50k-row sample of the full national GTFS
  static feed (the full file is ~300MB). Download the complete file from
  the Transport for Ireland GTFS static feed if you need full route
  coverage for the report/demo.
- `LOCAL_MODE` (`STREAM_BACKEND=local`, the default) lets the entire
  pipeline run without AWS credentials — see `docs/aws_services.md`.
