-- Athena table definitions over the S3 batch-layer output.
-- Run these once (Athena console or `aws athena start-query-execution`)
-- after infrastructure/kinesis_s3/setup_s3.py has created the bucket and
-- pyspark_jobs/batch_processor_emr.py has written output under
-- s3://<bucket>/batch-output/.

CREATE DATABASE IF NOT EXISTS bus_reliability;

CREATE EXTERNAL TABLE IF NOT EXISTS bus_reliability.batch_per_route (
    route_id            string,
    average_score        double,
    total_trips          bigint,
    min_score            int,
    max_score             int
)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
LOCATION 's3://REPLACE_WITH_YOUR_BUCKET/batch-output/per_route/';

CREATE EXTERNAL TABLE IF NOT EXISTS bus_reliability.batch_status_distribution (
    status               string,
    total_trips          bigint,
    avg_stop_updates     double
)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
LOCATION 's3://REPLACE_WITH_YOUR_BUCKET/batch-output/status_distribution/';

-- Speed layer output (written to S3 by speed_layer/lambda_function.py on
-- every invocation, see SUMMARY_S3_BUCKET / SUMMARY_S3_KEY env vars).
CREATE EXTERNAL TABLE IF NOT EXISTS bus_reliability.speed_worst_routes (
    route_id             string,
    avg_score            double,
    event_count          int
)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
LOCATION 's3://REPLACE_WITH_YOUR_BUCKET/speed-layer/worst-routes/';
