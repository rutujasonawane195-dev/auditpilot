#!/bin/bash
# ==============================================================================
# AuditPilot Stage 4: Remote Deploy Script invoked by Jenkins
# Dispatches /opt/auditpilot/deploy.sh $BUILD_NUMBER to the App Server via AWS SSM
# Implements Slide 29 from "PART 2 · SHIP IT ON AWS"
# ==============================================================================
set -e

export AWS_REGION="${AWS_REGION:-ap-south-1}"
BUILD_NUM="${BUILD_NUMBER:-latest}"

echo "Deploying build number: $BUILD_NUM to AWS region: $AWS_REGION"

# Locate running app server instance
ID=$(aws ec2 describe-instances --region "$AWS_REGION" \
  --filters Name=tag:Name,Values=auditpilot_app Name=instance-state-name,Values=running \
  --query 'Reservations[0].Instances[0].InstanceId' --output text)

if [ -z "$ID" ] || [ "$ID" = "None" ]; then
  echo "ERROR: No running EC2 instance with tag Name=auditpilot_app found in $AWS_REGION"
  exit 1
fi

echo "Found running app server instance: $ID"

# Send deploy command via AWS Systems Manager RunShellScript
CMD=$(aws ssm send-command --region "$AWS_REGION" --instance-ids "$ID" \
  --document-name AWS-RunShellScript \
  --parameters commands="/opt/auditpilot/deploy.sh $BUILD_NUM" \
  --query Command.CommandId --output text)

echo "Dispatched SSM Command: $CMD. Awaiting execution status..."
sleep 5

# Poll status for up to 5 minutes (60 iterations * 5s)
for i in $(seq 1 60); do
  S=$(aws ssm get-command-invocation --region "$AWS_REGION" --command-id "$CMD" \
    --instance-id "$ID" --query Status --output text 2>/dev/null || true)
  echo "Iteration $i/60 - SSM Status: $S"
  if [ "$S" = "Success" ]; then
    echo "Deployment succeeded! Container is healthy on instance $ID."
    exit 0
  fi
  if [ "$S" = "Failed" ] || [ "$S" = "Cancelled" ] || [ "$S" = "TimedOut" ]; then
    echo "SSM Command execution failed with status: $S"
    break
  fi
  sleep 5
done

echo "=== Deployment Error Logs from Target Server ==="
aws ssm get-command-invocation --region "$AWS_REGION" --command-id "$CMD" \
  --instance-id "$ID" --query StandardErrorContent --output text 2>/dev/null || true

exit 1
