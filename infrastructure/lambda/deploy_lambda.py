"""
Packages speed_layer/lambda_function.py + shared/ modules into a zip,
creates/updates the Lambda function, and wires it to the Kinesis stream via
an event source mapping (this is what makes AWS invoke it automatically per
batch of new records).

Usage:
    S3_BUCKET=my-bus-reliability-bucket \
    LAMBDA_ROLE_ARN=arn:aws:iam::<account>:role/bus-reliability-lambda-role \
    KINESIS_STREAM_ARN=arn:aws:kinesis:us-east-1:<account>:stream/bus-trip-stream \
    python infrastructure/lambda/deploy_lambda.py
"""

import os
import shutil
import zipfile
from pathlib import Path

import boto3

REGION = os.getenv("AWS_REGION", "us-east-1")
FUNCTION_NAME = os.getenv("LAMBDA_FUNCTION_NAME", "bus-reliability-speed-layer")
ROLE_ARN = os.environ["LAMBDA_ROLE_ARN"]
KINESIS_STREAM_ARN = os.environ["KINESIS_STREAM_ARN"]
S3_BUCKET = os.environ["S3_BUCKET"]
WINDOW_SECONDS = os.getenv("WINDOW_SECONDS", "300")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BUILD_DIR = REPO_ROOT / "build" / "lambda_speed_layer"
ZIP_PATH = REPO_ROOT / "build" / "lambda_speed_layer.zip"


def build_package():
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir(parents=True)

    shutil.copy(REPO_ROOT / "speed_layer" / "lambda_function.py", BUILD_DIR / "lambda_function.py")
    shutil.copytree(REPO_ROOT / "shared", BUILD_DIR / "shared")

    if ZIP_PATH.exists():
        ZIP_PATH.unlink()

    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in BUILD_DIR.rglob("*"):
            zf.write(path, path.relative_to(BUILD_DIR))

    print(f"Lambda package built: {ZIP_PATH}")
    return ZIP_PATH


def deploy(zip_path):
    client = boto3.client("lambda", region_name=REGION)

    with open(zip_path, "rb") as f:
        zip_bytes = f.read()

    existing = client.list_functions().get("Functions", [])
    exists = any(f["FunctionName"] == FUNCTION_NAME for f in existing)

    env_vars = {
        "WINDOW_SECONDS": WINDOW_SECONDS,
        "SUMMARY_S3_BUCKET": S3_BUCKET,
        "SUMMARY_S3_KEY": "speed-layer/speed_output.json",
    }

    if exists:
        client.update_function_code(FunctionName=FUNCTION_NAME, ZipFile=zip_bytes)
        client.update_function_configuration(
            FunctionName=FUNCTION_NAME, Environment={"Variables": env_vars}
        )
        print(f"Updated existing function '{FUNCTION_NAME}'.")
    else:
        client.create_function(
            FunctionName=FUNCTION_NAME,
            Runtime="python3.12",
            Role=ROLE_ARN,
            Handler="lambda_function.handler",
            Code={"ZipFile": zip_bytes},
            Timeout=30,
            MemorySize=256,
            Environment={"Variables": env_vars},
        )
        print(f"Created function '{FUNCTION_NAME}'.")

    mappings = client.list_event_source_mappings(FunctionName=FUNCTION_NAME).get(
        "EventSourceMappings", []
    )
    already_mapped = any(m["EventSourceArn"] == KINESIS_STREAM_ARN for m in mappings)

    if not already_mapped:
        client.create_event_source_mapping(
            EventSourceArn=KINESIS_STREAM_ARN,
            FunctionName=FUNCTION_NAME,
            StartingPosition="LATEST",
            BatchSize=25,
            MaximumBatchingWindowInSeconds=2,
        )
        print("Kinesis event source mapping created "
              "(batch size=25, max batching window=2s).")
    else:
        print("Event source mapping already exists.")


if __name__ == "__main__":
    zip_path = build_package()
    deploy(zip_path)
