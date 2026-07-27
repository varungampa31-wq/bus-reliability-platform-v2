"""
Creates the DynamoDB table + GSI + TTL config that the Lambda speed layer
depends on (infrastructure/lambda/dynamodb_table.json).
"""

import json
import os

import boto3

REGION = os.getenv("AWS_REGION", "us-east-1")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "dynamodb_table.json")


def main():
    with open(CONFIG_PATH) as f:
        config = json.load(f)
    config.pop("_comment", None)
    ttl_spec = config.pop("TimeToLiveSpecification")

    client = boto3.client("dynamodb", region_name=REGION)
    table_name = config["TableName"]

    existing = client.list_tables().get("TableNames", [])
    if table_name in existing:
        print(f"Table '{table_name}' already exists.")
    else:
        client.create_table(BillingMode="PROVISIONED", **config)
        client.get_waiter("table_exists").wait(TableName=table_name)
        print(f"Table '{table_name}' created.")

    client.update_time_to_live(
        TableName=table_name,
        TimeToLiveSpecification=ttl_spec,
    )
    print(f"TTL enabled on attribute '{ttl_spec['AttributeName']}'.")


if __name__ == "__main__":
    main()
