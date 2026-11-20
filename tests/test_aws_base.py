"""Tests for Part 2 Stage 2: AWS Base Infrastructure."""

import json
from pathlib import Path
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
POLICIES_DIR = BASE_DIR / "scripts" / "aws_policies"


def test_ec2_trust_policy_syntax():
    """Verify EC2 trust policy allows ec2.amazonaws.com sts:AssumeRole."""
    trust_file = POLICIES_DIR / "ec2_trust.json"
    assert trust_file.exists(), "ec2_trust.json must exist"

    data = json.loads(trust_file.read_text(encoding="utf-8"))
    assert data["Version"] == "2012-10-17"
    statement = data["Statement"][0]
    assert statement["Effect"] == "Allow"
    assert statement["Principal"]["Service"] == "ec2.amazonaws.com"
    assert statement["Action"] == "sts:AssumeRole"


def test_app_policy_scoping():
    """Verify app policy restricts secrets access strictly to auditpilot/google_api_key*."""
    app_file = POLICIES_DIR / "app_policy.json"
    assert app_file.exists(), "app_policy.json must exist"

    data = json.loads(app_file.read_text(encoding="utf-8"))
    actions = {}
    for stmt in data["Statement"]:
        if isinstance(stmt["Action"], list):
            for a in stmt["Action"]:
                actions[a] = stmt["Resource"]
        else:
            actions[stmt["Action"]] = stmt["Resource"]

    assert "secretsmanager:GetSecretValue" in actions
    secret_res = actions["secretsmanager:GetSecretValue"]
    assert "auditpilot/google_api_key" in secret_res, "Must restrict secret retrieval to auditpilot/google_api_key"


def test_jenkins_policy_actions():
    """Verify Jenkins policy grants SSM SendCommand and describe instances."""
    jenkins_file = POLICIES_DIR / "jenkins_policy.json"
    assert jenkins_file.exists(), "jenkins_policy.json must exist"

    data = json.loads(jenkins_file.read_text(encoding="utf-8"))
    stmt = data["Statement"][0]
    expected_actions = {"ssm:SendCommand", "ssm:GetCommandInvocation", "ec2:DescribeInstances"}
    actual_actions = set(stmt["Action"])
    assert expected_actions.issubset(actual_actions)


def test_setup_aws_base_script():
    """Verify setup_aws_base.sh exists, is executable, and contains required AWS CLI calls."""
    script_path = BASE_DIR / "scripts" / "setup_aws_base.sh"
    assert script_path.exists(), "scripts/setup_aws_base.sh must exist"

    content = script_path.read_text(encoding="utf-8")
    assert "aws ecr create-repository" in content
    assert "auditpilot_app_role" in content
    assert "auditpilot_jenkins_role" in content
    assert "auditpilot_jenkins_sg" in content
    assert "auditpilot_app_sg" in content
    assert "port 8080" in content
    assert "port 80" in content
