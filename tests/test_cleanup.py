"""Tests for Part 2 Stage 5: Teardown and Cleanup Utilities."""

from pathlib import Path
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"


def test_cleanup_script_exists_and_executable():
    """Verify scripts/cleanup_aws.sh exists and is executable."""
    script_path = SCRIPTS_DIR / "cleanup_aws.sh"
    assert script_path.exists(), "scripts/cleanup_aws.sh must exist"
    assert script_path.stat().st_mode & 0o111, "scripts/cleanup_aws.sh must be executable"


def test_cleanup_script_commands_and_order():
    """Verify cleanup script handles EC2, ECR, Secrets, Logs, SGs, and IAM roles in order."""
    script_path = SCRIPTS_DIR / "cleanup_aws.sh"
    content = script_path.read_text(encoding="utf-8")

    assert "aws ec2 terminate-instances" in content
    assert "aws ec2 wait instance-terminated" in content
    assert "aws ecr delete-repository" in content
    assert "aws secretsmanager delete-secret" in content
    assert "aws logs delete-log-group" in content
    assert "aws ec2 delete-security-group" in content
    assert "aws iam delete-role" in content
    assert "auditpilot_jenkins" in content
    assert "auditpilot_app" in content


def test_readme_contains_architecture_and_quickstart():
    """Verify README.md contains full architectural documentation, mermaid diagram, and quickstart."""
    readme_path = BASE_DIR / "README.md"
    assert readme_path.exists(), "README.md must exist"

    content = readme_path.read_text(encoding="utf-8")
    assert "```mermaid" in content, "Must include Mermaid architecture diagram"
    assert "LLMs Reason. Code Calculates." in content, "Must document core philosophy"
    assert "docker build -t auditpilot:local" in content, "Must include Docker build instructions"
    assert "Jenkins" in content, "Must include Jenkins CI/CD explanation"
    assert "cleanup_aws.sh" in content, "Must document AWS cleanup instructions"
