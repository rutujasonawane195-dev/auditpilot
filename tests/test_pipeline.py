"""Tests for Part 2 Stage 4: Jenkins CI/CD Pipeline."""

from pathlib import Path
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent


def test_jenkinsfile_exists_and_configured():
    """Verify Jenkinsfile defines pipeline, environment, and all 5 stages."""
    jenkinsfile = BASE_DIR / "Jenkinsfile"
    assert jenkinsfile.exists(), "Jenkinsfile must exist in repo root"

    content = jenkinsfile.read_text(encoding="utf-8")
    assert "pipeline {" in content, "Must be a declarative pipeline"
    assert "stage('Checkout')" in content, "Checkout stage must exist"
    assert "stage('Build image')" in content, "Build image stage must exist"
    assert "stage('Run tests')" in content, "Run tests stage must exist"
    assert "stage('Push to ECR')" in content, "Push to ECR stage must exist"
    assert "stage('Deploy')" in content, "Deploy stage must exist"
    assert "docker image prune -f" in content, "Post-build pruning must exist"
    assert "docker run --rm $IMAGE:$BUILD_NUMBER pytest -q" in content, "Must test image before pushing"


def test_deploy_remote_script_structure():
    """Verify scripts/deploy_remote.sh targets auditpilot_app and invokes deploy.sh via SSM."""
    deploy_script = BASE_DIR / "scripts" / "deploy_remote.sh"
    assert deploy_script.exists(), "scripts/deploy_remote.sh must exist"

    content = deploy_script.read_text(encoding="utf-8")
    assert "aws ec2 describe-instances" in content
    assert "tag:Name,Values=auditpilot_app" in content
    assert "aws ssm send-command" in content
    assert "/opt/auditpilot/deploy.sh" in content
    assert "aws ssm get-command-invocation" in content
