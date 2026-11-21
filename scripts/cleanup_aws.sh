#!/usr/bin/env bash
# ==============================================================================
# AuditPilot Cleanup Script: Delete All AWS Resources to Stop Billing
# Implements Slides 37 & 38 from "PART 2 · SHIP IT ON AWS"
# ==============================================================================
set -euo pipefail

export AWS_REGION="${AWS_REGION:-ap-south-1}"
export REPO="auditpilot"

AUTO_CONFIRM="${1:-}"
if [ "$AUTO_CONFIRM" != "--force" ]; then
  echo "=== WARNING: This script will terminate all AuditPilot AWS resources ==="
  read -p "Are you sure you want to proceed? (y/N): " -r CONFIRM
  if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "Cleanup aborted."
    exit 0
  fi
fi

echo "=== 1. Terminating EC2 Instances ==="
JENKINS_ID=$(aws ec2 describe-instances --region "$AWS_REGION" \
  --filters Name=tag:Name,Values=auditpilot_jenkins Name=instance-state-name,Values=pending,running,stopping,stopped \
  --query 'Reservations[].Instances[].InstanceId' --output text 2>/dev/null || true)

APP_ID=$(aws ec2 describe-instances --region "$AWS_REGION" \
  --filters Name=tag:Name,Values=auditpilot_app Name=instance-state-name,Values=pending,running,stopping,stopped \
  --query 'Reservations[].Instances[].InstanceId' --output text 2>/dev/null || true)

INSTANCE_IDS=""
if [ -n "$JENKINS_ID" ]; then INSTANCE_IDS="$INSTANCE_IDS $JENKINS_ID"; fi
if [ -n "$APP_ID" ]; then INSTANCE_IDS="$INSTANCE_IDS $APP_ID"; fi

if [ -n "$INSTANCE_IDS" ]; then
  echo "Terminating instances:$INSTANCE_IDS"
  aws ec2 terminate-instances --instance-ids $INSTANCE_IDS --region "$AWS_REGION"
  echo "Waiting for instances to terminate completely (required before deleting security groups)..."
  aws ec2 wait instance-terminated --instance-ids $INSTANCE_IDS --region "$AWS_REGION"
  echo "Instances terminated."
else
  echo "No active EC2 instances found."
fi

echo "=== 2. Deleting ECR Repository ==="
aws ecr delete-repository --repository-name "$REPO" --force --region "$AWS_REGION" 2>/dev/null || true

echo "=== 3. Deleting Secrets Manager Secret ==="
aws secretsmanager delete-secret \
  --secret-id "auditpilot/google_api_key" \
  --force-delete-without-recovery \
  --region "$AWS_REGION" 2>/dev/null || true

echo "=== 4. Deleting CloudWatch Log Group ==="
aws logs delete-log-group --log-group-name "auditpilot" --region "$AWS_REGION" 2>/dev/null || true

echo "=== 5. Deleting Security Groups ==="
for SG_NAME in auditpilot_jenkins_sg auditpilot_app_sg; do
  SG_ID=$(aws ec2 describe-security-groups --group-names "$SG_NAME" --region "$AWS_REGION" --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null || true)
  if [ -n "$SG_ID" ] && [ "$SG_ID" != "None" ]; then
    echo "Deleting Security Group $SG_NAME ($SG_ID)..."
    aws ec2 delete-security-group --group-id "$SG_ID" --region "$AWS_REGION" 2>/dev/null || true
  fi
done

echo "=== 6. Deleting IAM Roles and Instance Profiles ==="
for R in app jenkins; do
  P="auditpilot_${R}_role"
  PROF="auditpilot_${R}_profile"
  echo "Cleaning up IAM role and profile for $R..."

  # Detach managed policies
  ATTACHED=$(aws iam list-attached-role-policies --role-name "$P" --query 'AttachedPolicies[].PolicyArn' --output text 2>/dev/null || true)
  for A in $ATTACHED; do
    aws iam detach-role-policy --role-name "$P" --policy-arn "$A" 2>/dev/null || true
  done

  # Delete inline policy
  aws iam delete-role-policy --role-name "$P" --policy-name "${R}_inline" 2>/dev/null || true

  # Remove role from instance profile, then delete profile and role
  aws iam remove-role-from-instance-profile --instance-profile-name "$PROF" --role-name "$P" 2>/dev/null || true
  aws iam delete-instance-profile --instance-profile-name "$PROF" 2>/dev/null || true
  aws iam delete-role --role-name "$P" 2>/dev/null || true
done

echo "=== All AuditPilot AWS Resources Successfully Deleted ==="
