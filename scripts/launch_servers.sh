#!/usr/bin/env bash
# ==============================================================================
# AuditPilot Stage 3: Launch Jenkins and App Server Instances
# Implements Slides 21 & 24 from "PART 2 · SHIP IT ON AWS"
# ==============================================================================
set -euo pipefail

export AWS_REGION="${AWS_REGION:-ap-south-1}"
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_SCRIPTS="$DIR/server_scripts"

echo "=== 1. Discovering Security Group IDs ==="
JENKINS_SG=$(aws ec2 describe-security-groups --group-names auditpilot_jenkins_sg --region "$AWS_REGION" --query 'SecurityGroups[0].GroupId' --output text)
APP_SG=$(aws ec2 describe-security-groups --group-names auditpilot_app_sg --region "$AWS_REGION" --query 'SecurityGroups[0].GroupId' --output text)

echo "Jenkins Security Group: $JENKINS_SG"
echo "App Security Group:     $APP_SG"

echo "=== 2. Launching Jenkins Server (Ubuntu 24.04, t3.medium) ==="
UBUNTU_AMI=$(aws ssm get-parameters --names \
  /aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id \
  --region "$AWS_REGION" --query 'Parameters[0].Value' --output text)

JENKINS_ID=$(aws ec2 run-instances \
  --image-id "$UBUNTU_AMI" \
  --instance-type t3.medium \
  --security-group-ids "$JENKINS_SG" \
  --iam-instance-profile Name=auditpilot_jenkins_profile \
  --user-data "file://$SERVER_SCRIPTS/jenkins_userdata.sh" \
  --block-device-mappings 'DeviceName=/dev/sda1,Ebs={VolumeSize=20,VolumeType=gp3}' \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=auditpilot_jenkins}]' \
  --region "$AWS_REGION" \
  --query 'Instances[0].InstanceId' --output text)

echo "Launched Jenkins Instance: $JENKINS_ID"

echo "=== 3. Rendering App Server User Data Template ==="
TMP_APP_USERDATA="/tmp/app_userdata_rendered.sh"
sed "s/__REGION__/$AWS_REGION/g; s/__ACCOUNT__/$ACCOUNT_ID/g" "$SERVER_SCRIPTS/app_userdata.sh" > "$TMP_APP_USERDATA"

echo "=== 4. Launching App Server (Amazon Linux 2023, t3.small) ==="
AL_AMI=$(aws ssm get-parameters --names \
  /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64 \
  --region "$AWS_REGION" --query 'Parameters[0].Value' --output text)

APP_ID=$(aws ec2 run-instances \
  --image-id "$AL_AMI" \
  --instance-type t3.small \
  --security-group-ids "$APP_SG" \
  --iam-instance-profile Name=auditpilot_app_profile \
  --user-data "file://$TMP_APP_USERDATA" \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=auditpilot_app}]' \
  --region "$AWS_REGION" \
  --query 'Instances[0].InstanceId' --output text)

echo "Launched App Instance: $APP_ID"

echo "=== Stage 3 Complete: Both Servers Provisioned ==="
echo "Jenkins Instance ID: $JENKINS_ID (Ubuntu 24.04, 20GB GP3)"
echo "App Instance ID:     $APP_ID (AL2023, t3.small)"
echo "Connect to Jenkins via AWS Systems Manager Session Manager in ~5 minutes."
