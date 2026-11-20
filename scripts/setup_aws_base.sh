#!/usr/bin/env bash
# ==============================================================================
# AuditPilot Stage 2: AWS Base Infrastructure Setup Script
# Implements Slides 12-19 from "PART 2 · SHIP IT ON AWS"
# ==============================================================================
set -euo pipefail

export AWS_REGION="${AWS_REGION:-ap-south-1}"
export AWS_DEFAULT_REGION="$AWS_REGION"
export REPO="auditpilot"

echo "=== 1. Checking Environment and Identity ==="
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "AWS Account ID: $ACCOUNT_ID"
echo "AWS Region:     $AWS_REGION"

# Auto-detect or prompt for public IP
if [ -z "${MY_IP:-}" ]; then
  DETECTED_IP=$(curl -s https://checkip.amazonaws.com || true)
  if [ -n "$DETECTED_IP" ]; then
    MY_IP="${DETECTED_IP}/32"
  else
    echo "ERROR: Unable to detect public IP. Please set MY_IP=<your_ip>/32"
    exit 1
  fi
fi
echo "Authorized IP:  $MY_IP"

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POLICIES_DIR="$DIR/aws_policies"

echo "=== 2. Creating ECR Repository ==="
aws ecr describe-repositories --repository-names "$REPO" --region "$AWS_REGION" >/dev/null 2>&1 || \
aws ecr create-repository \
  --repository-name "$REPO" \
  --image-scanning-configuration scanOnPush=true \
  --region "$AWS_REGION"

REGISTRY_URI=$(aws ecr describe-repositories --repository-names "$REPO" --region "$AWS_REGION" --query 'repositories[0].repositoryUri' --output text)
echo "ECR Repository URI: $REGISTRY_URI"

echo "=== 3. Creating Secrets Manager Secret ==="
if [ -n "${GKEY:-}" ]; then
  aws secretsmanager describe-secret --secret-id "auditpilot/google_api_key" --region "$AWS_REGION" >/dev/null 2>&1 || \
  aws secretsmanager create-secret \
    --name "auditpilot/google_api_key" \
    --secret-string "$GKEY" \
    --region "$AWS_REGION"
  echo "Secret auditpilot/google_api_key created successfully."
else
  echo "Note: GKEY not supplied. Skipping secret creation (create manually or pass GKEY=...)."
fi

echo "=== 4. Creating App Server Role and Instance Profile ==="
aws iam get-role --role-name auditpilot_app_role >/dev/null 2>&1 || \
aws iam create-role --role-name auditpilot_app_role \
  --assume-role-policy-document "file://$POLICIES_DIR/ec2_trust.json"

for P in AmazonSSMManagedInstanceCore AmazonEC2ContainerRegistryReadOnly; do
  aws iam attach-role-policy \
    --role-name auditpilot_app_role \
    --policy-arn "arn:aws:iam::aws:policy/$P" || true
done

# Prepare inline policy with account and region substituted
APP_POLICY_DOC=$(sed "s/__REGION__/$AWS_REGION/g; s/__ACCOUNT__/$ACCOUNT_ID/g" "$POLICIES_DIR/app_policy.json")
aws iam put-role-policy --role-name auditpilot_app_role \
  --policy-name app_inline --policy-document "$APP_POLICY_DOC"

aws iam get-instance-profile --instance-profile-name auditpilot_app_profile >/dev/null 2>&1 || \
aws iam create-instance-profile --instance-profile-name auditpilot_app_profile

aws iam add-role-to-instance-profile \
  --instance-profile-name auditpilot_app_profile \
  --role-name auditpilot_app_role 2>/dev/null || true

echo "=== 5. Creating Jenkins Role and Instance Profile ==="
aws iam get-role --role-name auditpilot_jenkins_role >/dev/null 2>&1 || \
aws iam create-role --role-name auditpilot_jenkins_role \
  --assume-role-policy-document "file://$POLICIES_DIR/ec2_trust.json"

for P in AmazonSSMManagedInstanceCore AmazonEC2ContainerRegistryPowerUser; do
  aws iam attach-role-policy \
    --role-name auditpilot_jenkins_role \
    --policy-arn "arn:aws:iam::aws:policy/$P" || true
done

aws iam put-role-policy \
  --role-name auditpilot_jenkins_role \
  --policy-name jenkins_inline \
  --policy-document "file://$POLICIES_DIR/jenkins_policy.json"

aws iam get-instance-profile --instance-profile-name auditpilot_jenkins_profile >/dev/null 2>&1 || \
aws iam create-instance-profile --instance-profile-name auditpilot_jenkins_profile

aws iam add-role-to-instance-profile \
  --instance-profile-name auditpilot_jenkins_profile \
  --role-name auditpilot_jenkins_role 2>/dev/null || true

echo "=== 6. Creating Security Groups ==="
VPC_ID=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --region "$AWS_REGION" --query 'Vpcs[0].VpcId' --output text)
echo "Default VPC ID: $VPC_ID"

JENKINS_SG=$(aws ec2 describe-security-groups --group-names auditpilot_jenkins_sg --region "$AWS_REGION" --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null || \
aws ec2 create-security-group \
  --group-name auditpilot_jenkins_sg --description "Jenkins CI/CD Server" \
  --vpc-id "$VPC_ID" --region "$AWS_REGION" --query GroupId --output text)

APP_SG=$(aws ec2 describe-security-groups --group-names auditpilot_app_sg --region "$AWS_REGION" --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null || \
aws ec2 create-security-group \
  --group-name auditpilot_app_sg --description "AuditPilot App Server" \
  --vpc-id "$VPC_ID" --region "$AWS_REGION" --query GroupId --output text)

# Authorize ports to MY_IP only
aws ec2 authorize-security-group-ingress \
  --group-id "$JENKINS_SG" --protocol tcp --port 8080 --cidr "$MY_IP" --region "$AWS_REGION" 2>/dev/null || true

aws ec2 authorize-security-group-ingress \
  --group-id "$APP_SG" --protocol tcp --port 80 --cidr "$MY_IP" --region "$AWS_REGION" 2>/dev/null || true

echo "=== Stage 2 Complete ==="
echo "Jenkins Security Group: $JENKINS_SG (port 8080 open only to $MY_IP)"
echo "App Security Group:     $APP_SG (port 80 open only to $MY_IP)"
echo "ECR Repository:         $REGISTRY_URI"
