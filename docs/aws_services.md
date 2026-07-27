# AWS Services Used

| Service | Role | Where in code |
|---|---|---|
| **Kinesis Data Streams** | Ingestion — receives paced-replay records from the producer | `shared/stream_client.py` (`KinesisStreamClient`), `infrastructure/kinesis_s3/setup_kinesis.py` |
| **Amazon EMR (PySpark) + EMR managed scaling** | Batch layer — full-history correctness view | `pyspark_jobs/batch_processor_emr.py`, `infrastructure/emr/launch_cluster.py`, `infrastructure/emr/managed_scaling_policy.json` |
| **AWS Lambda** | Speed layer — real-time per-record + windowed aggregation, triggered by Kinesis | `speed_layer/lambda_function.py`, `infrastructure/lambda/deploy_lambda.py` |
| **DynamoDB (with TTL)** | Sliding-window state store for the Lambda speed layer | `infrastructure/lambda/dynamodb_table.json`, `infrastructure/lambda/setup_dynamodb.py` |
| **S3** | Raw archive, batch layer output, speed layer snapshots | `infrastructure/kinesis_s3/setup_s3.py` |
| **Athena** | Serving layer — SQL merge of batch + speed views | `athena/create_tables.sql`, `athena/merged_view.sql` |
| **EC2 Auto Scaling Group** | Hosts the producer + Flask dashboard, target-tracking on CPU | `infrastructure/ec2_asg/create_asg.py`, `infrastructure/ec2_asg/user_data.sh` |
| **CloudWatch** | Scaling metrics (ASG CPU, EMR YARN pending memory) used to justify scaling triggers in the report | n/a (native to EMR/ASG, view via console) |
| **Flask** | Dashboard reading the merged serving view | `flask_api/app.py` |

## Auto-scaling — triggers and cooldowns (stated explicitly per the rubric)

**EMR managed scaling** (batch cluster):
- Metric: YARN pending memory (EMR's built-in managed-scaling signal), evaluated ~every 60s.
- Bounds: `MinimumCapacityUnits=1`, `MaximumCapacityUnits=6`, `MaximumCoreCapacityUnits=4` (see `managed_scaling_policy.json`).
- Cooldowns: EMR managed scaling defaults — 300s scale-out cooldown, 300s scale-in cooldown.

**EC2 Auto Scaling Group** (producer/Flask):
- Policy: target tracking, `ASGAverageCPUUtilization` target = 50%.
- Bounds: `MinSize=1`, `MaxSize=4`, `DesiredCapacity=1`.
- Cooldowns: 120s default cooldown between scaling activities, 120s estimated instance warmup before it counts toward the metric.

## LOCAL_MODE (development / demo without AWS)

Set `STREAM_BACKEND=local` (the default). The pipeline then uses:
- `LocalStreamClient` (file-based pseudo-stream) instead of Kinesis
- `speed_layer/local_speed_consumer.py` instead of the Lambda handler
- `pyspark_jobs/batch_processor_local.py` instead of the EMR job
- `serving/merge_view.py` reading local JSON files instead of Athena

This lets every layer run and be demoed on a laptop with no AWS credentials, satisfying the "store the data, then replay it at a controlled rate" rule your lecturers confirmed counts as a real stream. Switch `STREAM_BACKEND=kinesis` and run the `infrastructure/` scripts to deploy the same logic for real on AWS.
