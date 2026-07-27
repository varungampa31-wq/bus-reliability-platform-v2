# Deployment Guide (personal AWS account)

## 0. Local demo first (no AWS needed)

```bash
pip install -r requirements.txt
python -m producer.producer            # builds dataset, replays into local pseudo-stream
python -m speed_layer.local_speed_consumer &   # windowed speed layer (run for a bit, then Ctrl+C)
python pyspark_jobs/batch_processor_local.py   # batch layer
python -m serving.merge_view            # merged serving view
python -m flask_api.app                 # dashboard at http://localhost:5000
```

## 1. Real AWS deployment

1. `aws configure` with a personal account that has permissions for Kinesis,
   S3, EMR, Lambda, DynamoDB, EC2, IAM.
2. Create the S3 bucket and Kinesis stream:
   ```bash
   export S3_BUCKET=your-unique-bucket-name
   python infrastructure/kinesis_s3/setup_s3.py
   python infrastructure/kinesis_s3/setup_kinesis.py
   ```
3. Create the DynamoDB table for the speed layer window state:
   ```bash
   python infrastructure/lambda/setup_dynamodb.py
   ```
4. Deploy the Lambda speed layer (needs an IAM role with
   `dynamodb:PutItem`, `dynamodb:Query`, `s3:PutObject`,
   `kinesis:GetRecords`/`DescribeStream`/etc — AWS attaches the Kinesis
   permissions automatically via the event source mapping's execution role):
   ```bash
   export LAMBDA_ROLE_ARN=arn:aws:iam::<account-id>:role/bus-reliability-lambda-role
   export KINESIS_STREAM_ARN=arn:aws:kinesis:us-east-1:<account-id>:stream/bus-trip-stream
   python infrastructure/lambda/deploy_lambda.py
   ```
5. Upload the EMR batch script and launch the cluster:
   ```bash
   aws s3 cp pyspark_jobs/batch_processor_emr.py s3://$S3_BUCKET/scripts/
   export EMR_SUBNET_ID=subnet-xxxxxxxx
   python infrastructure/emr/launch_cluster.py
   ```
6. Create the Athena tables + merged view (replace the bucket placeholder
   in the SQL first):
   ```bash
   # Athena console, or aws athena start-query-execution, using
   # athena/create_tables.sql then athena/merged_view.sql
   ```
7. Launch the producer/Flask Auto Scaling Group:
   ```bash
   export AMI_ID=ami-xxxxxxxx
   export SUBNET_IDS=subnet-aaa,subnet-bbb
   python infrastructure/ec2_asg/create_asg.py
   ```
8. Set `STREAM_BACKEND=kinesis` and a real `GTFS_API_KEY` in `.env` on the
   EC2 instance (or via the ASG launch template) to run against the live
   feed instead of the stored seed dataset.

## 2. Running the benchmark suite (for the report's Phase 3 section)

```bash
python benchmark/benchmark_batch.py    # edit BENCHMARK_WORKER_COUNTS for your hardware
python benchmark/benchmark_speed.py
python benchmark/plot_results.py       # writes PNGs to benchmark/results/
```
