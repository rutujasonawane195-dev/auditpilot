#!/bin/bash
# AuditPilot App Server Bootstrap and Deploy Script
# Implements Slides 22 & 23 from AuditPilot Part 2
set -e

dnf install -y docker
systemctl enable --now docker
mkdir -p /opt/auditpilot

cat > /opt/auditpilot/deploy.sh <<'DEPLOY'
#!/bin/bash
set -e
export HOME=/root
REGION=__REGION__
REGISTRY=__ACCOUNT__.dkr.ecr.$REGION.amazonaws.com
IMAGE=$REGISTRY/auditpilot:${1:-latest}

# Authenticate to ECR and pull image
aws ecr get-login-password --region $REGION | \
  docker login --username AWS --password-stdin $REGISTRY
docker pull $IMAGE || exit 1

# Fetch Gemini API key from AWS Secrets Manager
KEY=$(aws secretsmanager get-secret-value --region $REGION \
  --secret-id auditpilot/google_api_key \
  --query SecretString --output text)

# Deploy container with CloudWatch logs driver
docker rm -f auditpilot 2>/dev/null || true
docker run -d --name auditpilot --restart unless-stopped \
  -p 80:8080 \
  -e GOOGLE_API_KEY="$KEY" \
  -e GOOGLE_GENAI_USE_VERTEXAI=FALSE \
  --log-driver awslogs \
  --log-opt awslogs-region=$REGION \
  --log-opt awslogs-group=auditpilot \
  --log-opt awslogs-create-group=true $IMAGE

# Poll health endpoint until healthy (max 60 seconds)
for i in $(seq 1 20); do
  if curl -fs http://localhost/health >/dev/null 2>&1; then
    echo "Health check succeeded."
    exit 0
  fi
  sleep 3
done

echo "health check failed"
exit 1
DEPLOY

chmod +x /opt/auditpilot/deploy.sh
