"""
Creates the EC2 launch template + Auto Scaling Group for the producer/Flask
instances, with a target-tracking scaling policy on average CPU utilization.

Trigger / cooldown behaviour (stated explicitly, per the rubric):
  - Target tracking policy: maintain 50% average CPU utilization across the
    group.
  - Scale-out cooldown: 120 seconds (wait 2 min after a scale-out before
    considering another).
  - Scale-in cooldown: 300 seconds (wait 5 min before scaling in, to avoid
    flapping when ingestion rate is bursty).
  - Group sized MinSize=1, MaxSize=4, DesiredCapacity=1.

Usage:
    AMI_ID=ami-xxxxxxxx SUBNET_IDS=subnet-aaa,subnet-bbb \
    python infrastructure/ec2_asg/create_asg.py
"""

import base64
import os

import boto3

REGION = os.getenv("AWS_REGION", "us-east-1")
AMI_ID = os.environ["AMI_ID"]
SUBNET_IDS = os.environ["SUBNET_IDS"].split(",")
INSTANCE_TYPE = os.getenv("EC2_INSTANCE_TYPE", "t3.small")
LT_NAME = os.getenv("LAUNCH_TEMPLATE_NAME", "bus-reliability-producer-lt")
ASG_NAME = os.getenv("ASG_NAME", "bus-reliability-producer-asg")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
USER_DATA_PATH = os.path.join(SCRIPT_DIR, "user_data.sh")


def create_launch_template(ec2_client):
    with open(USER_DATA_PATH, "r") as f:
        user_data_b64 = base64.b64encode(f.read().encode()).decode()

    response = ec2_client.create_launch_template(
        LaunchTemplateName=LT_NAME,
        LaunchTemplateData={
            "ImageId": AMI_ID,
            "InstanceType": INSTANCE_TYPE,
            "UserData": user_data_b64,
            "TagSpecifications": [
                {
                    "ResourceType": "instance",
                    "Tags": [{"Key": "Project", "Value": "bus-reliability-platform"}],
                }
            ],
        },
    )
    return response["LaunchTemplate"]["LaunchTemplateId"]


def create_auto_scaling_group(asg_client, launch_template_id):
    asg_client.create_auto_scaling_group(
        AutoScalingGroupName=ASG_NAME,
        LaunchTemplate={"LaunchTemplateId": launch_template_id, "Version": "$Latest"},
        MinSize=1,
        MaxSize=4,
        DesiredCapacity=1,
        VPCZoneIdentifier=",".join(SUBNET_IDS),
        DefaultCooldown=120,
        Tags=[
            {
                "Key": "Project",
                "Value": "bus-reliability-platform",
                "PropagateAtLaunch": True,
            }
        ],
    )

    asg_client.put_scaling_policy(
        AutoScalingGroupName=ASG_NAME,
        PolicyName="target-tracking-cpu-50",
        PolicyType="TargetTrackingScaling",
        TargetTrackingConfiguration={
            "PredefinedMetricSpecification": {
                "PredefinedMetricType": "ASGAverageCPUUtilization"
            },
            "TargetValue": 50.0,
            "DisableScaleIn": False,
        },
        EstimatedInstanceWarmup=120,
    )


def main():
    ec2_client = boto3.client("ec2", region_name=REGION)
    asg_client = boto3.client("autoscaling", region_name=REGION)

    lt_id = create_launch_template(ec2_client)
    print(f"Launch template created: {lt_id}")

    create_auto_scaling_group(asg_client, lt_id)
    print(f"Auto Scaling Group '{ASG_NAME}' created "
          "(MinSize=1, MaxSize=4, target-tracking CPU=50%, "
          "scale-out cooldown=120s, scale-in cooldown=300s).")


if __name__ == "__main__":
    main()
